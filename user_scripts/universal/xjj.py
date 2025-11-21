# 第三方库
from httpx import AsyncClient
from pyrogram import filters, Client
from pyrogram.types.messages_and_media import Message


async def get_video_url():
    async with AsyncClient() as session:
        response = await session.get("https://tucdn.wpon.cn/api-girl/index.php?wpon=json", timeout=30.0)
    if response.status_code != 200:
        return None, "连接出错。。。"      
    data = response.json()
    return "https:" + data["mp4"]



@Client.on_message(                                                                    
        filters.me
        & filters.command("xjj", prefixes=[",", "，"])
    )
async def xjj(client: Client, message: Message):
    if message.chat and message.chat.id in []:
        # 用户群禁止使用此功能
        code_message = await message.edit("本群禁止使用此功能。")
        return
    code_message = await message.edit("小姐姐视频生成中 . . .")
    try:
        url = await get_video_url()
        try:
            await message.reply_video(
                url,
                quote=False,
                reply_to_message_id=message.reply_to_message_id,
            )
            await code_message.delete()
        except Exception as e:
            await message.edit(f"出错了呜呜呜 ~ {e.__class__.__name__}")
    except Exception as e:
        await message.edit(f"出错了呜呜呜 ~ {e.__class__.__name__}")