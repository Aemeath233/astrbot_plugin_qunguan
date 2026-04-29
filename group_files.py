from urllib.parse import quote

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .common import get_client


async def collect_all_files(client, group_id: int):
    """递归收集群文件（根目录 + 所有子文件夹），返回文件列表。"""
    all_files = []

    root = await client.api.call_action("get_group_root_files", group_id=group_id)
    files = root.get("files", []) or []
    folders = root.get("folders", []) or []
    all_files.extend(files)

    for folder in folders:
        folder_id = folder.get("folder_id")
        if not folder_id:
            continue
        try:
            sub = await client.api.call_action(
                "get_group_files_by_folder",
                group_id=group_id,
                folder_id=folder_id,
            )
            sub_files = sub.get("files", []) or []
            for file in sub_files:
                file["_folder_name"] = folder.get("folder_name", "")
            all_files.extend(sub_files)
        except Exception as e:
            logger.warning(f"读取文件夹 {folder.get('folder_name')} 失败: {e}")

    return all_files


async def search_group_files(event: AstrMessageEvent, keyword: str) -> str:
    """在当前QQ群的群文件中搜索文件。"""
    try:
        client, group_id = await get_client(event)
        if client is None:
            return group_id

        all_files = await collect_all_files(client, int(group_id))
        if not all_files:
            return "当前群没有任何群文件。"

        keyword_lower = keyword.lower()
        matched = [
            file
            for file in all_files
            if keyword_lower in (file.get("file_name", "") or "").lower()
        ]

        if not matched:
            return f"未找到包含「{keyword}」的群文件。"

        if len(matched) == 1:
            file = matched[0]
            url_result = await client.api.call_action(
                "get_group_file_url",
                group_id=int(group_id),
                file_id=file["file_id"],
                busid=file["busid"],
            )
            url = fix_download_url(url_result.get("url", ""), file["file_name"])
            folder = file.get("_folder_name", "根目录")
            return (
                f"找到唯一匹配文件：\n"
                f"文件名：{file['file_name']}\n"
                f"大小：{format_size(file.get('file_size', 0))}\n"
                f"位置：{folder}\n"
                f"下载链接：{url}"
            )

        result_lines = [f"找到 {len(matched)} 个匹配「{keyword}」的文件："]
        for index, file in enumerate(matched[:20], 1):
            folder = file.get("_folder_name", "根目录")
            size = format_size(file.get("file_size", 0))
            result_lines.append(f"{index}. {file['file_name']}（{size}，{folder}）")
        if len(matched) > 20:
            result_lines.append(f"...还有 {len(matched) - 20} 个文件未显示")
        result_lines.append("\n请告诉用户有多个匹配结果，让用户说出具体要哪个文件的完整文件名。")
        return "\n".join(result_lines)
    except Exception as e:
        logger.error(f"搜索群文件失败: {e}")
        return f"失败：搜索群文件出错，原因：{e}"


async def get_group_file_link(event: AstrMessageEvent, file_name: str) -> str:
    """根据精确的文件名获取QQ群文件的下载链接。"""
    try:
        client, group_id = await get_client(event)
        if client is None:
            return group_id

        all_files = await collect_all_files(client, int(group_id))

        target = None
        for file in all_files:
            if file.get("file_name", "") == file_name:
                target = file
                break

        if not target:
            file_name_lower = file_name.lower()
            for file in all_files:
                if (file.get("file_name", "") or "").lower() == file_name_lower:
                    target = file
                    break

        if not target:
            return f"未找到文件名为「{file_name}」的群文件，请确认文件名是否正确。"

        url_result = await client.api.call_action(
            "get_group_file_url",
            group_id=int(group_id),
            file_id=target["file_id"],
            busid=target["busid"],
        )
        url = fix_download_url(url_result.get("url", ""), target["file_name"])
        return (
            f"文件名：{target['file_name']}\n"
            f"大小：{format_size(target.get('file_size', 0))}\n"
            f"下载链接：{url}"
        )
    except Exception as e:
        logger.error(f"获取群文件链接失败: {e}")
        return f"失败：获取群文件链接出错，原因：{e}"


def fix_download_url(url: str, file_name: str) -> str:
    """修复下载链接，在 fname= 后补上文件名。"""
    if not url:
        return "获取链接失败"
    if url.endswith("fname="):
        url += quote(file_name)
    return url


def format_size(size_bytes: int) -> str:
    """将字节数格式化为可读的文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f}MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f}GB"
