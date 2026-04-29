from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .common import get_client


async def at_all_members(event: AstrMessageEvent, message: str) -> str:
    """在当前QQ群中艾特全体成员并发送一条消息。"""
    client, group_id = await get_client(event)
    if client is None:
        return group_id

    try:
        payloads = {
            "group_id": int(group_id),
            "message": [
                {"type": "at", "data": {"qq": "all"}},
                {"type": "text", "data": {"text": f" {message}"}},
            ],
        }
        await client.api.call_action("send_group_msg", **payloads)
        logger.info(f"已在群 {group_id} 艾特全体成员: {message}")
        return f"成功：已艾特全体成员并发送消息「{message}」。"
    except Exception as e:
        logger.error(f"艾特全体成员失败: {e}")
        return f"失败：艾特全体成员出错，原因：{e}"
