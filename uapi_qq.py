import os
from datetime import datetime, timezone, timedelta
from typing import Any

from astrbot.api import logger


DEFAULT_UAPI_BASE_URL = "https://uapis.cn"
DEFAULT_UAPI_TIMEOUT_SECONDS = 15


async def query_qq_user_info(
    qq: str,
    *,
    token: str = "",
    base_url: str = DEFAULT_UAPI_BASE_URL,
    timeout_seconds: int = DEFAULT_UAPI_TIMEOUT_SECONDS,
) -> str:
    """通过 UAPI 查询 QQ 用户公开信息。"""
    qq = str(qq).strip()
    if not qq.isdigit():
        return "失败：请提供有效的 QQ 号，例如 12345678。"

    token = _resolve_token(token)
    if not token:
        return "失败：未配置 UAPI Token，请在插件配置 uapi_token 中填写，或设置环境变量 UAPI_TOKEN。"

    try:
        data = await _request_qq_user_info(
            qq,
            token=token,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
        user = _unwrap_user_data(data)
        if not user:
            return f"未查询到 QQ {qq} 的用户信息。"
        return _format_qq_user_info(user, qq)
    except Exception as e:
        logger.error(f"查询QQ用户信息失败: {e}")
        return f"失败：查询QQ用户信息出错，原因：{e}"


async def _request_qq_user_info(
    qq: str,
    *,
    token: str,
    base_url: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    import aiohttp

    url = f"{base_url.rstrip('/')}/api/v1/social/qq/userinfo"
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params={"qq": qq}, headers=headers) as response:
            text = await response.text()
            if response.status >= 400:
                raise RuntimeError(f"UAPI 返回 HTTP {response.status}: {text[:200]}")
            try:
                data = await response.json(content_type=None)
            except Exception as e:
                raise RuntimeError(f"UAPI 响应不是 JSON: {text[:200]}") from e

    if not isinstance(data, dict):
        raise RuntimeError("UAPI 响应格式异常。")
    return data


def _resolve_token(token: str) -> str:
    return str(token or os.getenv("UAPI_TOKEN", "")).strip()


def _unwrap_user_data(data: dict[str, Any]) -> dict[str, Any]:
    code = data.get("code")
    success = data.get("success")
    message = str(data.get("message") or data.get("msg") or "").strip()

    if success is False:
        raise RuntimeError(message or "UAPI 返回失败。")
    if code not in (None, 0, "0"):
        raise RuntimeError(message or f"UAPI 返回错误码：{code}")

    nested = data.get("data")
    if isinstance(nested, dict):
        return nested
    return data


def _format_qq_user_info(user: dict[str, Any], fallback_qq: str) -> str:
    qq = _value(user, "qq", fallback=fallback_qq)
    lines = [f"QQ用户信息：{qq}"]

    fields = [
        ("昵称", "nickname"),
        ("个性签名", "long_nick"),
        ("年龄", "age"),
        ("性别", "sex"),
        ("QQ个性域名", "qid"),
        ("QQ等级", "qq_level"),
        ("所在地", "location"),
        ("QQ邮箱", "email"),
        ("VIP", "is_vip"),
        ("VIP等级", "vip_level"),
        ("注册时间", "reg_time"),
        ("最后更新", "last_updated"),
        ("头像", "avatar_url"),
    ]

    for label, key in fields:
        value = user.get(key)
        if value in (None, ""):
            continue
        if key in {"reg_time", "last_updated"}:
            value = _format_time(str(value))
        elif key == "is_vip":
            value = "是" if bool(value) else "否"
        lines.append(f"{label}：{value}")

    if len(lines) == 1:
        return f"未查询到 QQ {qq} 的可展示用户信息。"
    return "\n".join(lines)


def _format_time(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return text
        china_time = dt.astimezone(timezone(timedelta(hours=8)))
        return china_time.strftime("%Y-%m-%d %H:%M:%S UTC+08:00")
    except ValueError:
        return text


def _value(data: dict[str, Any], key: str, *, fallback: str = "") -> str:
    value = data.get(key)
    if value in (None, ""):
        return fallback
    return str(value)
