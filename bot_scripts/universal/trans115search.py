# 标准库

# 第三方库
from pyrogram import Client, filters
from pyrogram.types import Message

# 自定义模块
from config.config import MY_TGID
from libs.state import state_manager

# 配置表头
SECTION = "TRAN115SEARCH"


# 命令处理：设置转发规则 /transmsgset chatid
@Client.on_message(filters.chat(MY_TGID) & filters.command("trans115search"))
async def basic_set(client: Client, message: Message):
    # 检查命令参数
    args = message.text.split()
    if len(args) != 2:
        await message.reply(
            "使用格式: \n`/trans115search` chatid\n`/trans115search off`"
        )
        return
    try:
        chat_id = int(args[1])
        state_manager.set_section(SECTION, {"chat_id": chat_id})
        await message.reply(f"已设置: 监听爱影搜索群 转发到 {chat_id}")
    except ValueError:
        if args[1] == "off":
            await message.reply(f"监听已关闭")
            state_manager.set_section(SECTION, {})
            return
        await message.reply("参数必须为数字 ID")
    except Exception as e:
        await message.reply(f"设置失败: {str(e)}")
