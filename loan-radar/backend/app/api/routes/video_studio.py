from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_current_user
from app.models import AiGeneratedAsset, ModelConfig, Task, User
from app.schemas.common import paginated
from app.services.ai_service import ImageAiClient, OpenAICompatibleImageClient
from app.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video-studio", tags=["video-studio"])


def _find_ffmpeg() -> str | None:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
    extra_dirs = []
    tools_root = os.environ.get("LOAN_RADAR_TOOLS_DIR", "")
    if tools_root:
        extra_dirs.append(os.path.join(tools_root, "ffmpeg"))
    resources_path = os.environ.get("ELECTRON_RESOURCES_PATH", "")
    if resources_path:
        extra_dirs.append(os.path.join(resources_path, "tools", "ffmpeg"))
    for candidate in extra_dirs:
        exe = os.path.join(candidate, "ffmpeg.exe") if os.name == "nt" else os.path.join(candidate, "ffmpeg")
        if os.path.isfile(exe):
            return exe
    return None


def _find_ffprobe() -> str | None:
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        return ffprobe_path
    extra_dirs = []
    tools_root = os.environ.get("LOAN_RADAR_TOOLS_DIR", "")
    if tools_root:
        extra_dirs.append(os.path.join(tools_root, "ffmpeg"))
    resources_path = os.environ.get("ELECTRON_RESOURCES_PATH", "")
    if resources_path:
        extra_dirs.append(os.path.join(resources_path, "tools", "ffmpeg"))
    for candidate in extra_dirs:
        exe = os.path.join(candidate, "ffprobe.exe") if os.name == "nt" else os.path.join(candidate, "ffprobe")
        if os.path.isfile(exe):
            return exe
    return None


def _media_dir() -> Path:
    return Path(get_settings().storage_dir) / "media"


def _video_prefix(user: User) -> str:
    return f"xhs-video-u{user.id}-"


def _video_type(file_name: str) -> str:
    lower = file_name.lower()
    if lower.endswith(".mp4"):
        return "video/mp4"
    if lower.endswith(".mov"):
        return "video/quicktime"
    if lower.endswith(".avi"):
        return "video/x-msvideo"
    if lower.endswith(".mkv"):
        return "video/x-matroska"
    return "application/octet-stream"


class ExtractCoverRequest(BaseModel):
    video_file_name: str = Field(min_length=1, max_length=180)
    timestamp_seconds: float = Field(default=0.0, ge=0)
    width: int = Field(default=1080, ge=128, le=3840)
    height: int = Field(default=1440, ge=128, le=3840)


class DescribeVideoRequest(BaseModel):
    video_url: str = Field(min_length=1, max_length=4000)
    instruction: str = Field(default="", max_length=800)


class ListVideosRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


def _validate_video_owner(file_name: str, user: User) -> str:
    if Path(file_name).name != file_name or ".." in file_name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    valid_prefixes = (_video_prefix(user), f"xhs-upload-u{user.id}-")
    if not file_name.startswith(valid_prefixes):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file_name


def _ffprobe_duration(video_path: Path) -> float:
    ffprobe = _find_ffprobe()
    if not ffprobe:
        return 0.0
    try:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=10,
        )
        info = json.loads(result.stdout)
        return float(info.get("format", {}).get("duration", 0))
    except Exception:
        return 0.0


def _ffmpeg_extract_frame(video_path: Path, output_path: Path, timestamp: float, width: int, height: int) -> bool:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return False
    try:
        cmd = [
            ffmpeg, "-y",
            "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0 and output_path.is_file()
    except Exception as exc:
        logger.warning("ffmpeg extract frame failed: %s", exc)
        return False


@router.get("/videos")
def list_videos(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_current_user),
):
    prefix = f"xhs-upload-u{current_user.id}-"
    video_prefix = _video_prefix(current_user)
    media_dir = _media_dir()
    video_exts = {".mp4", ".mov", ".avi", ".mkv"}
    files: list[dict[str, Any]] = []

    if media_dir.is_dir():
        for f in sorted(media_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.suffix.lower() in video_exts and (f.name.startswith(prefix) or f.name.startswith(video_prefix)):
                duration = _ffprobe_duration(f)
                files.append({
                    "file_name": f.name,
                    "url": f"/api/files/media/{f.name}",
                    "size": f.stat().st_size,
                    "duration": round(duration, 2),
                    "media_type": _video_type(f.name),
                })

    total = len(files)
    start = (page - 1) * page_size
    end = start + page_size
    return paginated(files[start:end], page, page_size, total)


@router.delete("/videos/{file_name}")
def delete_video(file_name: str, current_user: User = Depends(require_current_user)):
    _validate_video_owner(file_name, current_user)
    file_path = _media_dir() / file_name
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    file_path.unlink()
    return success_response({"file_name": file_name, "status": "deleted"})


@router.post("/extract-cover")
def extract_cover(
    payload: ExtractCoverRequest,
    current_user: User = Depends(require_current_user),
):
    video_file_name = _validate_video_owner(payload.video_file_name, current_user)
    video_path = _media_dir() / video_file_name
    if not video_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file not found")

    cover_file_name = f"{_video_prefix(current_user)}cover-{uuid4().hex}.jpg"
    cover_path = _media_dir() / cover_file_name
    _media_dir().mkdir(parents=True, exist_ok=True)

    success = _ffmpeg_extract_frame(video_path, cover_path, payload.timestamp_seconds, payload.width, payload.height)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="封面提取失败，请确认已安装 ffmpeg 且视频文件有效",
        )

    return success_response({
        "file_name": cover_file_name,
        "download_url": f"/api/files/media/{cover_file_name}",
        "width": payload.width,
        "height": payload.height,
    })


@router.post("/describe")
def describe_video(
    payload: DescribeVideoRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    model_config = db.scalar(
        select(ModelConfig).where(
            ModelConfig.user_id == current_user.id,
            ModelConfig.model_type.in_(["image", "multimodal"]),
            ModelConfig.is_active.is_(True),
        ).order_by(ModelConfig.id.desc())
    )
    if model_config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先配置多模态模型（如 GPT-4o）以使用视频描述功能",
        )

    from app.core.security import decrypt_text
    api_key = decrypt_text(model_config.encrypted_api_key)

    task = Task(
        user_id=current_user.id,
        platform="xhs",
        task_type="ai_video_describe",
        status="running",
        progress=0,
        payload={"model_config_id": model_config.id, "video_url": payload.video_url[:200], "instruction": payload.instruction[:200]},
    )
    db.add(task)
    db.commit()

    try:
        client = OpenAICompatibleImageClient()
        instruction = payload.instruction or "描述这个视频的内容、风格和适合小红书发布的卖点方向。"
        text = client.describe_image(
            model_config=model_config,
            api_key=api_key,
            image_url=payload.video_url,
            instruction=instruction,
        )
        task.status = "completed"
        task.progress = 100
        task.payload = {**(task.payload or {}), "result_length": len(text)}
        db.commit()
        return {"text": text}
    except Exception as exc:
        task.status = "failed"
        task.progress = 100
        task.payload = {**(task.payload or {}), "error": str(exc)[:200]}
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"视频描述失败: {str(exc)[:200]}",
        ) from exc


@router.get("/video-assets")
def list_video_assets(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    assets = db.scalars(
        select(AiGeneratedAsset)
        .where(
            AiGeneratedAsset.user_id == current_user.id,
            AiGeneratedAsset.asset_type == "video",
        )
        .order_by(AiGeneratedAsset.created_at.desc())
    ).all()
    items = [
        {
            "id": a.id,
            "file_path": a.file_path,
            "prompt": a.prompt,
            "model_name": a.model_name,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in assets
    ]
    return paginated(items, page, page_size)
