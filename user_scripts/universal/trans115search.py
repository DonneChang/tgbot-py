# 标准库

# 第三方库
from pyrogram import Client, filters
from pyrogram.types import Message

# 自定义模块
from libs.state import state_manager
from app import get_bot_app

# 配置表头
SECTION = "TRAN115SEARCH"


# 消息监听和转发
def listen_115search_filter(_, __, m: Message):
    if state_manager.get_item(SECTION, "chat_id"):
        return bool(m.from_user.is_bot and m.chat.id == -1002466900287)


@Client.on_message(filters.create(listen_115search_filter) & filters.regex(r"列表"))
async def forward_message(client: Client, message: Message):
    chat_id = state_manager.get_item(SECTION, "chat_id")
    bot_app = get_bot_app()
    await bot_app.send_message(
        chat_id,
        text=message.caption if message.caption else message.text,
        entities=message.entities,
    )
