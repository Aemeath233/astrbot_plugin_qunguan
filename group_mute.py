from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .common import (
    get_client,
    is_astrbot_admin,
    normalize_qq,
    validate_qq,
)


MAX_MUTE_SECONDS = 25 * 24 * 60 * 60


def _to_non_negative_int(value, field_name: str) -> tuple[int | None, str | None]:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None, f"失败：{field_name} 必须是非负整数。"
    if normalized < 0:
        return None, f"失败：{field_name} 不能为负数。"
    return normalized, None


def _format_duration(total_seconds: int) -> str:
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}小时")
    if minutes:
        parts.append(f"{minutes}分钟")
    if seconds:
        parts.append(f"{seconds}秒")
    return "".join(parts) or "0秒"


def build_mute_duration(hours: int, minutes: int, seconds: int) -> tuple[int | None, str | None]:
    normalized_hours, error = _to_non_negative_int(hours, "hours")
    if error:
        return None, error
    normalized_minutes, error = _to_non_negative_int(minutes, "minutes")
    if error:
        return None, error
    normalized_seconds, error = _to_non_negative_int(seconds, "seconds")
    if error:
        return None, error

    assert normalized_hours is not None
    assert normalized_minutes is not None
    assert normalized_seconds is not None
    duration = (
        normalized_hours * 3600
        + normalized_minutes * 60
        + normalized_seconds
    )
    if duration <= 0:
        return None, "失败：禁言时长必须大于 0；如果要解禁，请使用解禁工具。"
    if duration > MAX_MUTE_SECONDS:
        return None, "失败：禁言时间太长了，最多只能禁言 25 天。"
    return duration, None


async def mute_group_member(
    event: AstrMessageEvent,
    user_id: str,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    """禁言QQ群成员。AstrBot 管理员可禁言任意成员，普通用户只能禁言自己。"""
    target_qq = normalize_qq(event, user_id, allow_self=True)
    invalid_reason = validate_qq(target_qq)
    if invalid_reason:
        return invalid_reason

    duration, error = build_mute_duration(hours, minutes, seconds)
    if error:
        return error
    assert duration is not None

    if not is_astrbot_admin(event) and target_qq != str(event.get_sender_id()):
        return "失败：只有 AstrBot 系统管理员可以禁言他人；普通用户只能禁言自己。"

    client, group_id = await get_client(event)
    if client is None:
        return group_id

    try:
        await client.api.call_action(
            "set_group_ban",
            group_id=int(group_id),
            user_id=int(target_qq),
            duration=duration,
        )
        duration_text = _format_duration(duration)
        logger.info(f"已将用户 {target_qq} 在群 {group_id} 禁言 {duration_text}")
        return f"成功：已将 {target_qq} 禁言 {duration_text}。"
    except Exception as e:
        logger.error(f"禁言群成员失败: {e}")
        return f"失败：禁言群成员出错，原因：{e}"


async def unmute_group_member(event: AstrMessageEvent, user_id: str) -> str:
    """解除QQ群成员禁言。仅 AstrBot 系统管理员可用。"""
    if not is_astrbot_admin(event):
        return "失败：只有 AstrBot 系统管理员可以解除群成员禁言。"

    target_qq = normalize_qq(event, user_id, allow_self=True)
    invalid_reason = validate_qq(target_qq)
    if invalid_reason:
        return invalid_reason

    client, group_id = await get_client(event)
    if client is None:
        return group_id

    try:
        await client.api.call_action(
            "set_group_ban",
            group_id=int(group_id),
            user_id=int(target_qq),
            duration=0,
        )
        logger.info(f"已解除用户 {target_qq} 在群 {group_id} 的禁言")
        return f"成功：已解除 {target_qq} 的群禁言。"
    except Exception as e:
        logger.error(f"解除群成员禁言失败: {e}")
        return f"失败：解除群成员禁言出错，原因：{e}"
