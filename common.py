from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent


SELF_ALIASES = {"", "我", "自己", "本人", "self", "me"}


async def get_client(event: AstrMessageEvent):
    """获取 OneBot 客户端，返回 (client, group_id) 或 (None, 错误信息)。"""
    group_id = event.get_group_id()
    if not group_id:
        return None, "失败：当前不在群聊中，此功能只能在群聊中使用。"
    if event.get_platform_name() != "aiocqhttp":
        return None, "失败：此功能仅支持 QQ 平台。"

    client = getattr(event, "bot", None)
    if client is None:
        return None, "失败：无法获取 QQ 平台客户端。"
    return client, group_id


async def get_qq_client(event: AstrMessageEvent):
    """获取 QQ 平台 OneBot 客户端，不要求当前事件必须来自群聊。"""
    if event.get_platform_name() != "aiocqhttp":
        return None, "失败：此功能仅支持 QQ 平台。"

    client = getattr(event, "bot", None)
    if client is None:
        return None, "失败：无法获取 QQ 平台客户端。"
    return client, ""


def normalize_qq(
    event: AstrMessageEvent,
    user_id: str,
    *,
    allow_self: bool = False,
) -> str:
    """将 LLM/命令传入的 QQ 号整理成纯数字字符串。"""
    target_qq = str(user_id).strip()
    if allow_self and target_qq in SELF_ALIASES:
        return str(event.get_sender_id())
    return target_qq


def is_astrbot_admin(event: AstrMessageEvent) -> bool:
    """判断消息发送者是否是 AstrBot 系统管理员。"""
    if hasattr(event, "is_admin"):
        return event.is_admin()
    return getattr(event, "role", "") == "admin"


async def get_group_member_role(client, group_id: int, user_id: int) -> str:
    """获取群成员角色，NapCat/OneBot 返回值通常是 owner/admin/member。"""
    member_info = await client.api.call_action(
        "get_group_member_info",
        group_id=group_id,
        user_id=user_id,
        no_cache=True,
    )
    return str(member_info.get("role", ""))


def validate_qq(user_id: str) -> str | None:
    if user_id.isdigit():
        return None
    return "失败：请提供有效的 QQ 号，例如 12345678。"


def log_role_check_failed(group_id: int, user_id: str, error: Exception) -> None:
    logger.warning(
        f"确认群成员角色失败: group_id={group_id}, user_id={user_id}, error={error}"
    )
