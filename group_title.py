from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .common import get_client


async def set_my_group_title(event: AstrMessageEvent, title: str) -> str:
    """修改调用者自己的QQ群专属头衔。"""
    client, group_id = await get_client(event)
    if client is None:
        return group_id

    try:
        user_id = event.get_sender_id()
        payloads = {
            "group_id": int(group_id),
            "user_id": int(user_id),
            "special_title": title,
            "duration": -1,
        }
        await client.api.call_action("set_group_special_title", **payloads)
        logger.info(f"已为用户 {user_id} 在群 {group_id} 设置头衔: {title}")

        if title:
            return f"成功：已将用户的群头衔修改为「{title}」。"
        return "成功：已清除用户的群头衔。"
    except Exception as e:
        logger.error(f"修改群头衔失败: {e}")
        return f"失败：修改群头衔出错，原因：{e}"
