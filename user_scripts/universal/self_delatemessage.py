# 标准库
import asyncio
import contextlib

# 第三方库
from pyrogram import filters, Client
from pyrogram.types import Message

"""
删除自己所发的消息
"""

@Client.on_message(
        filters.me
        & filters.command("dme", prefixes=",")
    )

async def self_delatemessage(client: Client, message: Message):
    """Deletes specific amount of messages you sent."""
    msgs = []
    count_buffer = 0
    offset = 0
    if len(message.command) != 2:
        if not message.reply_to_message:
            return await message.edit(f"命令格式不对请输入/dme number")
        offset = message.reply_to_message.id
    try:
        count = int(message.command[1])
        await message.delete()
    except ValueError:
        await message.edit(f"删除数量错误 请输出正整数")
        return
    async for msg in client.get_chat_history(message.chat.id, limit=100):
        if count_buffer == count:
            break
        if msg.from_user and msg.from_user.is_self:
            msgs.append(msg.id)
            count_buffer += 1
            if len(msgs) == 100:
                await client.delete_messages(message.chat.id, msgs)
                msgs = []
    async for msg in client.search_messages(
        message.chat.id, from_user="me", offset=offset
    ):
        if count_buffer == count:
            break
        msgs.append(msg.id)
        count_buffer += 1
        if len(msgs) == 100:
            await client.delete_messages(message.chat.id, msgs)
            msgs = []
    if msgs:
        await client.delete_messages(message.chat.id, msgs)   

    with contextlib.suppress(ValueError):
        notification = await send_prune_notify(client, message, count_buffer, count)
        await asyncio.sleep(1)
        await notification.delete()

async def send_prune_notify(client: Client, message: Message, count_buffer, count):
    return await message.reply(f"已删除消息{str(count_buffer)} / {str(count)}")