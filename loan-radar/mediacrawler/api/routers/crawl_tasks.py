# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..schemas import CrawlerStartRequest
from ..schemas.crawler import (
    CrawlerTypeEnum,
    LoginTypeEnum,
    PlatformEnum,
    SaveDataOptionEnum,
)
from ..schemas.raw_tasks import CrawlTaskCreateRequest, CrawlTaskResponse, RawListResponse
from ..services import crawler_manager
from ..services.raw_data_importer import RawDataImporter
from ..services.raw_task_store import RawTaskStore

router = APIRouter(prefix="/crawl-tasks", tags=["crawl-tasks"])
DATA_DIR = RawDataImporter().data_dir

_SOURCE_TYPE_TO_CRAWLER_TYPE = {
    "keyword": "search",
    "competitor_account": "creator",
    "manual_post": "detail",
}


@router.post("", response_model=CrawlTaskResponse)
async def create_crawl_task(request: CrawlTaskCreateRequest):
    store = RawTaskStore()
    crawler_type = _SOURCE_TYPE_TO_CRAWLER_TYPE[request.source_type]
    task = store.create_task(
        platform=request.platform,
        source_type=request.source_type,
        source_value=request.source_value,
        crawler_type=crawler_type,
    )

    if request.fixture is not None:
        store.mark_running(task["id"])
        for post in request.fixture.posts:
            store.insert_raw_post(
                task_id=task["id"],
                platform=request.platform,
                source_type=request.source_type,
                source_value=request.source_value,
                raw_id=post.raw_id,
                post_raw_id=post.post_raw_id,
                url=post.url,
                content_text=post.content_text,
                author_name=post.author_name,
                published_at=post.published_at,
                raw_data=post.raw_data,
            )
        for comment in request.fixture.comments:
            store.insert_raw_comment(
                task_id=task["id"],
                platform=request.platform,
                source_type=request.source_type,
                source_value=request.source_value,
                raw_id=comment.raw_id,
                post_raw_id=comment.post_raw_id,
                url=comment.url,
                content_text=comment.content_text,
                author_name=comment.author_name,
                published_at=comment.published_at,
                raw_data=comment.raw_data,
            )
        store.mark_success(task["id"])
        task = store.get_task(task["id"])
    else:
        store.mark_running(task["id"])
        started = await crawler_manager.start(_to_crawler_start_request(request, crawler_type))
        if not started:
            store.mark_failed(task["id"], "failed to start MediaCrawler process")
            raise HTTPException(status_code=500, detail="failed to start MediaCrawler process")
        task = store.get_task(task["id"])

    return task


@router.get("/{task_id}", response_model=CrawlTaskResponse)
async def get_crawl_task(task_id: int):
    store = RawTaskStore()
    _sync_running_task_if_finished(store, task_id)
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="crawl task not found")
    return task


@router.get("/{task_id}/raw-posts", response_model=RawListResponse)
async def list_raw_posts(
    task_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
):
    store = RawTaskStore()
    _sync_running_task_if_finished(store, task_id)
    if store.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="crawl task not found")
    return store.list_raw_posts(task_id, page=page, page_size=page_size)


@router.get("/{task_id}/raw-comments", response_model=RawListResponse)
async def list_raw_comments(
    task_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
):
    store = RawTaskStore()
    _sync_running_task_if_finished(store, task_id)
    if store.get_task(task_id) is None:
        raise HTTPException(status_code=404, detail="crawl task not found")
    return store.list_raw_comments(task_id, page=page, page_size=page_size)


def _to_crawler_start_request(
    request: CrawlTaskCreateRequest,
    crawler_type: str,
) -> CrawlerStartRequest:
    payload = {
        "platform": PlatformEnum(request.platform),
        "login_type": LoginTypeEnum(request.login_type),
        "crawler_type": CrawlerTypeEnum(crawler_type),
        "start_page": 1,
        "enable_comments": request.enable_comments,
        "enable_sub_comments": request.enable_sub_comments,
        "save_option": SaveDataOptionEnum.JSON,
        "cookies": request.cookies,
        "headless": request.headless,
    }
    if request.source_type == "keyword":
        payload["keywords"] = request.source_value
    elif request.source_type == "manual_post":
        payload["specified_ids"] = request.source_value
    elif request.source_type == "competitor_account":
        payload["creator_ids"] = request.source_value
    return CrawlerStartRequest(**payload)


def _sync_running_task_if_finished(store: RawTaskStore, task_id: int) -> None:
    task = store.get_task(task_id)
    if task is None or task["status"] != "running":
        return
    if crawler_manager.status == "running":
        return
    if crawler_manager.status == "error":
        error_message = crawler_manager.get_status().get("error_message") or "MediaCrawler process failed"
        store.mark_failed(task_id, error_message)
        return

    importer = RawDataImporter(data_dir=DATA_DIR, store=store)
    importer.import_latest_for_task(task_id)
