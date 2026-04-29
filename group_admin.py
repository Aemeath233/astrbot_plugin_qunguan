from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .common import (
    get_client,
    get_group_member_role,
    is_astrbot_admin,
    log_role_check_failed,
    normalize_qq,
    validate_qq,
)


async def can_unset_group_admin(
    event: AstrMessageEvent,
    client,
    group_id: int,
    target_qq: str,
) -> tuple[bool, str]:
    """取消管理员的权限判断。"""
    if is_astrbot_admin(event):
        return True, ""

    sender_id = str(event.get_sender_id())
    if target_qq != sender_id:
        return (
            False,
            "失败：只有 AstrBot 系统管理员可以取消他人的群管理员；"
            "QQ群管理员只能取消自己的管理员身份。",
        )

    try:
        sender_role = await get_group_member_role(client, group_id, int(sender_id))
    except Exception as e:
        log_role_check_failed(group_id, sender_id, e)
        return False, f"失败：无法确认你当前是否为QQ群管理员，原因：{e}"

    if sender_role != "admin":
        return False, "失败：你当前不是QQ群管理员，不能取消自己的管理员身份。"

    return True, ""


async def set_group_admin_status(
    event: AstrMessageEvent,
    target_qq: str,
    enable: bool,
) -> str:
    """设置或取消QQ群管理员，并统一处理权限校验。"""
    target_qq = normalize_qq(event, target_qq, allow_self=not enable)
    invalid_reason = validate_qq(target_qq)
    if invalid_reason:
        return invalid_reason

    client, group_id = await get_client(event)
    if client is None:
        return group_id

    group_id_int = int(group_id)
    target_qq_int = int(target_qq)

    if enable:
        if not is_astrbot_admin(event):
            return "失败：只有 AstrBot 系统管理员可以设置QQ群管理员。"
    else:
        allowed, reason = await can_unset_group_admin(
            event,
            client,
            group_id_int,
            target_qq,
        )
        if not allowed:
            return reason

    action_name = "设置" if enable else "取消"
    try:
        await client.api.call_action(
            "set_group_admin",
            group_id=group_id_int,
            user_id=target_qq_int,
            enable=enable,
        )
        if enable:
            logger.info(f"已将用户 {target_qq} 设置为群 {group_id} 的管理员")
            return f"成功：已将 {target_qq} 设置为QQ群管理员。"

        logger.info(f"已取消用户 {target_qq} 在群 {group_id} 的管理员")
        return f"成功：已取消 {target_qq} 的QQ群管理员。"
    except Exception as e:
        logger.error(f"{action_name}群管理员失败: {e}")
        return f"失败：{action_name}群管理员出错，原因：{e}"
