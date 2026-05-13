from __future__ import annotations

from fastapi import APIRouter

from app.collectors.xhs_browser_signer import XhsBrowserSigner
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/api/xhs-auth", tags=["xhs-auth"])


@router.get("/status")
def get_auth_status() -> dict:
    signer = XhsBrowserSigner.get_instance()
    status = signer.get_status()
    return success_response(data=status)


@router.post("/start-login")
def start_login(headless: bool = True) -> dict:
    signer = XhsBrowserSigner.get_instance()
    signer.headless = headless

    if not signer.is_started:
        try:
            signer.start()
        except Exception as error:
            return error_response(message=f"Failed to start browser: {error}")

    if signer.is_logged_in:
        return success_response(data={"logged_in": True, "message": "Already logged in"})

    try:
        qr_result = signer.get_qrcode()
        return success_response(data={
            "logged_in": False,
            "qr_code": qr_result.get("qr_code", ""),
            "qr_type": qr_result.get("type", ""),
            "message": "Please scan QR code with XHS app to login",
        })
    except Exception as error:
        return error_response(message=f"Failed to get QR code: {error}")


@router.get("/check-login")
def check_login() -> dict:
    signer = XhsBrowserSigner.get_instance()

    if not signer.is_started:
        return success_response(data={"logged_in": False, "message": "Browser not started"})

    try:
        result = signer.check_login_status()
        return success_response(data=result)
    except Exception as error:
        return error_response(message=f"Failed to check login status: {error}")


@router.post("/refresh-qrcode")
def refresh_qrcode() -> dict:
    signer = XhsBrowserSigner.get_instance()

    if not signer.is_started:
        return error_response(message="Browser not started, call /start-login first")

    if signer.is_logged_in:
        return success_response(data={"logged_in": True, "message": "Already logged in"})

    try:
        qr_result = signer.get_qrcode()
        return success_response(data={
            "logged_in": False,
            "qr_code": qr_result.get("qr_code", ""),
            "qr_type": qr_result.get("type", ""),
            "message": "Please scan QR code with XHS app to login",
        })
    except Exception as error:
        return error_response(message=f"Failed to refresh QR code: {error}")


@router.post("/logout")
def logout() -> dict:
    XhsBrowserSigner.reset_instance()
    return success_response(data={"message": "Browser session cleared, please login again"})


@router.post("/restart")
def restart_browser(headless: bool = True) -> dict:
    XhsBrowserSigner.reset_instance()
    signer = XhsBrowserSigner.get_instance()
    signer.headless = headless

    try:
        signer.start()
    except Exception as error:
        return error_response(message=f"Failed to restart browser: {error}")

    status = signer.get_status()
    return success_response(data=status)
