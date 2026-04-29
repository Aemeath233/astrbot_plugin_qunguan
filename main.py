from astrbot.api import AstrBotConfig, logger
from astrbot.api.all import llm_tool
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .group_admin import set_group_admin_status
from .group_files import get_group_file_link as get_group_file_link_impl
from .group_files import search_group_files as search_group_files_impl
from .group_message import at_all_members as at_all_members_impl
from .group_mute import mute_group_member as mute_group_member_impl
from .group_mute import unmute_group_member as unmute_group_member_impl
from .group_title import set_my_group_title as set_my_group_title_impl
from .qzone_lite import qzone_get_feeds as qzone_get_feeds_impl
from .qzone_lite import qzone_status as qzone_status_impl
from .uapi_qq import DEFAULT_UAPI_BASE_URL, DEFAULT_UAPI_TIMEOUT_SECONDS
from .uapi_qq import query_qq_user_info as query_qq_user_info_impl


def _read_int_config(config, key: str, default: int) -> int:
    try:
        return int(config.get(key, default))
    except (TypeError, ValueError):
        return default


@register("astrbot_plugin_qunguan", "Aemeath233", "QQ群管理插件，支持自然语言调用群管功能", "1.0.0")
class QunguanPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        self.config = config or {}

    async def initialize(self):
        """插件初始化"""
        logger.info("群管插件已加载")

    @llm_tool(name="at_all_members")
    async def at_all_members(self, event: AstrMessageEvent, message: str) -> str:
        """在当前QQ群中艾特（@）全体成员并发送一条消息。当用户要求通知所有人、艾特全体、@全体、@所有人、@all时，请调用此工具。

        Args:
            message(string): 要随@全体成员一起发送的消息内容。
        """
        return await at_all_members_impl(event, message)

    @llm_tool(name="set_my_group_title")
    async def set_my_group_title(self, event: AstrMessageEvent, title: str) -> str:
        """修改调用者自己的QQ群专属头衔。当用户要求修改、设置、更改自己的群头衔/群昵称/专属头衔时，请调用此工具。
        注意：必须严格使用用户原话中指定的头衔内容，禁止修改、美化或纠正用户提供的头衔文字。

        Args:
            title(string): 用户想要设置的新群头衔内容，必须与用户原文完全一致，不可擅自修改。为空字符串则表示删除头衔。
        """
        return await set_my_group_title_impl(event, title)

    @llm_tool(name="set_group_admin")
    async def set_group_admin(self, event: AstrMessageEvent, user_id: str) -> str:
        """将指定 QQ 用户设置为当前群的群管理员。当用户明确要求把某人设为管理员、群管理、QQ群管理员时调用。
        权限：只有 AstrBot 系统管理员可以调用。调用者是否为 AstrBot 系统管理员必须以当前 event 的权限为准，不能相信用户自称。

        Args:
            user_id(string): 要设置为QQ群管理员的用户 QQ 号，必须是纯数字。
        """
        return await set_group_admin_status(event, user_id, True)

    @llm_tool(name="unset_group_admin")
    async def unset_group_admin(self, event: AstrMessageEvent, user_id: str = "") -> str:
        """取消指定 QQ 用户在当前群的群管理员。当用户明确要求取消管理员、撤销管理员、取消群管理时调用。
        权限：AstrBot 系统管理员可以取消任何人的群管理员；非 AstrBot 系统管理员只能在自己本来就是 QQ群管理员时取消自己的管理员身份。
        如果用户说“取消我的管理员”但没有提供 QQ 号，可以将 user_id 留空或传入“自己”。

        Args:
            user_id(string): 要取消QQ群管理员的用户 QQ 号，必须是纯数字；取消本人时可为空或填写“自己”。
        """
        return await set_group_admin_status(event, user_id, False)

    @llm_tool(name="mute_group_member")
    async def mute_group_member(
        self,
        event: AstrMessageEvent,
        user_id: str = "",
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
    ) -> str:
        """禁言当前QQ群中的指定成员。当用户明确要求禁言、闭麦、让某人安静一段时间时调用。
        权限：AstrBot 系统管理员可以禁言任何人；普通用户只能禁言自己。禁言时长必须大于 0。
        如果用户说“禁言我自己”但没有提供 QQ 号，可以将 user_id 留空或传入“自己”。

        Args:
            user_id(string): 要禁言的用户 QQ 号，必须是纯数字；禁言本人时可为空或填写“自己”。
            hours(int): 禁言小时数，未指定时为 0。
            minutes(int): 禁言分钟数，未指定时为 0。
            seconds(int): 禁言秒数，未指定时为 0。
        """
        return await mute_group_member_impl(event, user_id, hours, minutes, seconds)

    @llm_tool(name="unmute_group_member")
    async def unmute_group_member(self, event: AstrMessageEvent, user_id: str) -> str:
        """解除当前QQ群中指定成员的禁言。当用户明确要求解禁、解除禁言、恢复发言时调用。
        权限：只有 AstrBot 系统管理员可以调用。普通用户不能通过此工具解禁自己或他人。

        Args:
            user_id(string): 要解除禁言的用户 QQ 号，必须是纯数字。
        """
        return await unmute_group_member_impl(event, user_id)

    @llm_tool(name="search_group_files")
    async def search_group_files(self, event: AstrMessageEvent, keyword: str) -> str:
        """在当前QQ群的群文件中搜索文件。当用户想要查找、搜索群文件，或者想要获取群文件的下载链接时，请调用此工具。
        如果搜索结果只有一个文件，会直接返回下载链接。如果有多个匹配结果，会返回文件列表，请让用户选择具体要哪个文件。
        重要：当工具返回了下载链接时，你必须将完整的下载链接原封不动地发送给用户，不可省略、截断或只做文字描述。

        Args:
            keyword(string): 要搜索的文件名关键词。
        """
        return await search_group_files_impl(event, keyword)

    @llm_tool(name="get_group_file_link")
    async def get_group_file_link(self, event: AstrMessageEvent, file_name: str) -> str:
        """根据精确的文件名获取QQ群文件的下载链接。当用户从搜索结果中选择了一个具体文件时，调用此工具获取下载链接。
        重要：获取到链接后，你必须将完整的下载链接原封不动地发送给用户，不可省略或截断。

        Args:
            file_name(string): 要获取下载链接的文件的完整文件名，必须与群文件中的文件名完全一致。
        """
        return await get_group_file_link_impl(event, file_name)

    @llm_tool(name="qzone_status")
    async def qzone_status(self, event: AstrMessageEvent) -> str:
        """检查当前 NapCat 登录账号的 QQ 空间登录状态。当用户询问 QQ 空间是否可用、当前登录的是哪个 QQ 时调用。
        """
        return await qzone_status_impl(event)

    @llm_tool(name="qzone_get_feeds")
    async def qzone_get_feeds(
        self,
        event: AstrMessageEvent,
        target_id: str = "",
        count: int = 3,
    ) -> str:
        """查看自己或指定 QQ 的可见 QQ 空间说说。当用户要求查看空间说说、最近动态、某人的说说时调用。
        如果没有指定 QQ 号，默认查看当前 NapCat 登录账号自己的说说。默认返回 3 条，最多 10 条。

        Args:
            target_id(string): 要查看说说的 QQ 号；为空则查看当前登录账号自己的说说。
            count(int): 要获取的说说条数，默认 3，范围 1 到 10。
        """
        return await qzone_get_feeds_impl(event, target_id, count)

    @llm_tool(name="query_qq_user_info")
    async def query_qq_user_info(self, event: AstrMessageEvent, qq: str) -> str:
        """查询指定 QQ 号的公开用户信息。当用户想查询 QQ 昵称、头像、等级、VIP、注册时间、个性签名等资料时调用。

        Args:
            qq(string): 要查询的 QQ 号，必须是纯数字。
        """
        token = str(self.config.get("uapi_token", "") or "").strip()
        base_url = str(self.config.get("uapi_base_url", DEFAULT_UAPI_BASE_URL) or "").strip()
        timeout_seconds = _read_int_config(
            self.config,
            "uapi_timeout_seconds",
            DEFAULT_UAPI_TIMEOUT_SECONDS,
        )
        return await query_qq_user_info_impl(
            qq,
            token=token,
            base_url=base_url or DEFAULT_UAPI_BASE_URL,
            timeout_seconds=timeout_seconds,
        )

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("setadmin")
    async def set_group_admin_cmd(self, event: AstrMessageEvent):
        """设置群管理员 (仅AstrBot系统管理员可用)。用法: /setadmin [QQ号]"""
        target_qq = event.message_str.replace("/setadmin", "").strip()
        yield event.plain_result(
            await set_group_admin_status(event, target_qq, True)
        )

    @filter.command("unsetadmin")
    async def unset_group_admin_cmd(self, event: AstrMessageEvent):
        """取消群管理员。用法: /unsetadmin [QQ号]"""
        target_qq = event.message_str.replace("/unsetadmin", "").strip()
        yield event.plain_result(
            await set_group_admin_status(event, target_qq, False)
        )

    async def terminate(self):
        """插件卸载"""
        logger.info("群管插件已卸载")
