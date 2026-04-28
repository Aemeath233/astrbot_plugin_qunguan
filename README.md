# astrbot_plugin_qunguan

QQ群管助手是一个面向 AstrBot 和 NapCat/aiocqhttp 的 QQ 群管理插件，支持通过自然语言触发 LLM tools 来扩展机器人在群聊里的管理能力。

## 支持环境

- AstrBot
- QQ 平台适配器：aiocqhttp
- NapCat 或其他兼容 OneBot v11 的 QQ 客户端
- 使用场景：QQ群聊

## 功能

- @全体成员并发送通知消息。
- 设置或清除调用者自己的QQ群专属头衔。
- 搜索当前群的群文件，并在唯一匹配时直接返回下载链接。
- 根据完整文件名获取群文件下载链接。
- 将指定 QQ 用户设置为QQ群管理员。
- 取消指定 QQ 用户的QQ群管理员。
- 禁言指定群成员，支持按小时、分钟、秒组合时长。
- 解除指定群成员禁言。

## LLM tools

插件功能主要通过 AstrBot 的 LLM tools 暴露，用户可以用自然语言表达需求，不需要记 slash 指令。

示例：

```text
通知全体明天晚上八点开会
帮我把群头衔改成 摸鱼大师
找一下群文件里的课表
把 12345678 设置为群管理员
取消我的管理员
取消 12345678 的管理员
把 12345678 禁言 10 分钟
禁言我自己 30 秒
解除 12345678 的禁言
```

对应工具：

- `at_all_members`：@全体成员并发送消息。
- `set_my_group_title`：设置或清除自己的群专属头衔。
- `search_group_files`：按关键词搜索群文件。
- `get_group_file_link`：根据完整文件名获取下载链接。
- `set_group_admin`：设置QQ群管理员。
- `unset_group_admin`：取消QQ群管理员。
- `mute_group_member`：禁言QQ群成员。
- `unmute_group_member`：解除QQ群成员禁言。

## 权限规则

设置或取消QQ群管理员时，插件会在工具函数内部做权限判断，不依赖用户自称身份。

- 设置QQ群管理员：仅 AstrBot 系统管理员可用。
- 取消QQ群管理员：
  - AstrBot 系统管理员可以取消任意用户的QQ群管理员。
  - 非 AstrBot 系统管理员只能在自己已经是QQ群管理员时，取消自己的管理员身份。
- 禁言QQ群成员：
  - AstrBot 系统管理员可以禁言任意群成员。
  - 普通用户只能禁言自己，不能禁言他人。
  - 禁言时长必须大于 0，且最多 25 天。
- 解除群成员禁言：仅 AstrBot 系统管理员可用。

注意：插件权限通过后，实际操作仍然需要机器人 QQ 在群里拥有足够权限。通常设置或取消群管理员要求机器人 QQ 是群主；禁言、解禁要求机器人 QQ 具备群管理权限，否则 NapCat/OneBot 会返回权限不足。

## 安装

将本仓库放入 AstrBot 的插件目录：

```text
data/plugins/astrbot_plugin_qunguan
```

然后在 AstrBot WebUI 中重载插件，或重启 AstrBot。

## 常见失败原因

- 当前消息不是群聊消息。
- 当前平台不是 QQ aiocqhttp。
- 机器人 QQ 不是群主，无法设置或取消QQ群管理员。
- 机器人 QQ 不是群主或管理员，无法禁言或解除禁言。
- 机器人 QQ 没有群文件、群头衔等相关操作权限。
- 目标 QQ 号不是纯数字，或目标用户不在当前群。
- 禁言时长为 0、负数，或超过 25 天。
- NapCat/OneBot 连接异常，导致接口调用失败。

## 相关链接

- [AstrBot](https://github.com/AstrBotDevs/AstrBot)
- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [NapCat](https://github.com/NapNeko/NapCatQQ)
