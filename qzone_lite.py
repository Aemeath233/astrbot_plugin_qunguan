import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .common import get_qq_client


QZONE_DOMAIN = "user.qzone.qq.com"
QZONE_BASE_URL = f"https://{QZONE_DOMAIN}"
QZONE_FEEDS_URL = (
    "https://user.qzone.qq.com/proxy/domain/taotao.qq.com/"
    "cgi-bin/emotion_cgi_msglist_v6"
)


@dataclass
class QzoneContext:
    uin: str
    skey: str
    p_skey: str
    cookies: dict[str, str]

    @property
    def gtk(self) -> int:
        token = self.p_skey or self.skey
        value = 5381
        for char in token:
            value += (value << 5) + ord(char)
        return value & 0x7FFFFFFF


async def qzone_status(event: AstrMessageEvent) -> str:
    """检查 QQ 空间登录状态。"""
    try:
        client, error = await get_qq_client(event)
        if client is None:
            return error

        ctx = await _get_qzone_context(client)
        nickname = await _get_login_nickname(client)
        nickname_text = f"（{nickname}）" if nickname else ""
        return (
            "成功：QQ空间登录状态可用。\n"
            f"当前登录 QQ：{ctx.uin}{nickname_text}\n"
            f"p_skey：{'已获取' if ctx.p_skey else '未获取'}\n"
            f"skey：{'已获取' if ctx.skey else '未获取'}"
        )
    except Exception as e:
        logger.error(f"检查QQ空间登录状态失败: {e}")
        return f"失败：检查QQ空间登录状态出错，原因：{e}"


async def qzone_get_feeds(
    event: AstrMessageEvent,
    target_id: str = "",
    count: int = 3,
) -> str:
    """获取自己或指定 QQ 的可见说说列表。"""
    try:
        client, error = await get_qq_client(event)
        if client is None:
            return error

        ctx = await _get_qzone_context(client)
        target_id = str(target_id).strip() or ctx.uin
        if not target_id.isdigit():
            return "失败：请提供有效的 QQ 号，例如 12345678。"

        try:
            count_int = int(count)
        except (TypeError, ValueError):
            return "失败：获取条数必须是 1 到 10 之间的整数。"
        if count_int < 1 or count_int > 10:
            return "失败：获取条数必须是 1 到 10 之间的整数。"

        data = await _request_feeds(ctx, target_id, count_int)
        msglist = data.get("msglist") or []
        if not msglist:
            return f"未找到 QQ {target_id} 的可见说说。"

        lines = [f"QQ {target_id} 最近 {min(len(msglist), count_int)} 条可见说说："]
        for index, item in enumerate(msglist[:count_int], 1):
            lines.append(_format_feed_item(index, item, target_id))
        return "\n\n".join(lines)
    except Exception as e:
        logger.error(f"获取QQ空间说说失败: {e}")
        return f"失败：获取QQ空间说说出错，原因：{e}"


async def _get_qzone_context(client) -> QzoneContext:
    result = await client.api.call_action("get_cookies", domain=QZONE_DOMAIN)
    cookies_str = str(result.get("cookies") or "").strip()
    if not cookies_str:
        raise RuntimeError("未获取到 QQ空间 Cookie，请确认 NapCat 登录状态。")

    cookie = SimpleCookie(cookies_str)
    cookies = {key: morsel.value for key, morsel in cookie.items()}
    uin = _normalize_cookie_uin(cookies.get("uin", ""))
    if not uin:
        raise RuntimeError("Cookie 中缺少合法 uin。")

    ctx = QzoneContext(
        uin=uin,
        skey=cookies.get("skey", ""),
        p_skey=cookies.get("p_skey", ""),
        cookies=cookies,
    )
    if not ctx.p_skey and not ctx.skey:
        raise RuntimeError("Cookie 中缺少 p_skey/skey，QQ空间登录状态可能不可用。")
    return ctx


async def _get_login_nickname(client) -> str:
    try:
        info = await client.api.call_action("get_login_info")
    except Exception:
        return ""
    return str(info.get("nickname") or "").strip()


async def _request_feeds(ctx: QzoneContext, target_id: str, count: int) -> dict[str, Any]:
    import aiohttp

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        ),
        "Referer": f"{QZONE_BASE_URL}/{target_id}",
    }
    params = {
        "g_tk": ctx.gtk,
        "uin": target_id,
        "ftype": 0,
        "sort": 0,
        "pos": 0,
        "num": count,
        "replynum": 20,
        "callback": "_preloadCallback",
        "code_version": 1,
        "format": "json",
        "need_comment": 1,
        "need_private_comment": 1,
    }

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(
            QZONE_FEEDS_URL,
            params=params,
            headers=headers,
            cookies=ctx.cookies,
        ) as response:
            text = await response.text()
            if response.status == 403:
                raise RuntimeError(f"无权限查看 QQ {target_id} 的说说。")
            if response.status >= 400:
                raise RuntimeError(f"QQ空间接口返回 HTTP {response.status}。")

    data = _parse_qzone_response(text)
    code = data.get("code")
    message = str(data.get("message") or data.get("msg") or "").strip()
    if code not in (None, 0):
        if message:
            raise RuntimeError(f"QQ空间接口返回错误：{message}")
        raise RuntimeError(f"QQ空间接口返回错误码：{code}")
    return data


def _parse_qzone_response(text: str) -> dict[str, Any]:
    raw = text.strip()
    if not raw:
        raise RuntimeError("QQ空间接口返回空响应。")

    match = re.match(r"^[\w$]+\((.*)\);?$", raw, flags=re.S)
    if match:
        raw = match.group(1).strip()
    elif not raw.startswith("{"):
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"解析 QQ空间响应失败：{e}") from e
    if not isinstance(data, dict):
        raise RuntimeError("QQ空间接口响应格式异常。")
    return data


def _format_feed_item(index: int, item: dict[str, Any], default_uin: str) -> str:
    nickname = str(
        item.get("name")
        or item.get("nickname")
        or item.get("nick")
        or item.get("uin")
        or default_uin
    )
    create_time = _format_feed_time(item)
    content = _clean_feed_text(
        str(
            item.get("content")
            or item.get("con")
            or item.get("summary")
            or ""
        )
    )
    tid = str(item.get("tid") or item.get("id") or "").strip()
    pic_count = _get_pic_count(item)

    lines = [f"{index}. {nickname}"]
    if create_time:
        lines.append(f"时间：{create_time}")
    if tid:
        lines.append(f"tid：{tid}")
    lines.append(f"内容：{content or '[无文字内容]'}")
    if pic_count:
        lines.append(f"图片：{pic_count} 张")
    return "\n".join(lines)


def _format_feed_time(item: dict[str, Any]) -> str:
    for key in ("created_time", "createTime", "abstime", "time"):
        value = item.get(key)
        if value is None:
            continue
        try:
            timestamp = int(value)
        except (TypeError, ValueError):
            continue
        if timestamp <= 0:
            continue
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return ""


def _clean_feed_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _get_pic_count(item: dict[str, Any]) -> int:
    pics = item.get("pic") or item.get("pictures") or item.get("images") or []
    if isinstance(pics, list):
        return len(pics)
    return 0


def _normalize_cookie_uin(raw_uin: str) -> str:
    value = str(raw_uin or "").strip()
    if not value:
        return ""
    if value[0].isalpha():
        value = value[1:]
    return value if value.isdigit() else ""
