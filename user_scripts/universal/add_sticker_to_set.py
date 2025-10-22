
# 标准库
import re
import asyncio
from random import randint, random
from datetime import datetime, time

# 第三方库
from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.raw import functions, types

# 自定义模块
from app import get_bot_app
from config.config import PT_GROUP_ID, MY_TGID, LOTTERY_TARGET_GROUP, PRIZE_LIST
from config.reply_message import (
    NO_AOUTOLOTTERY_REPLY_MESSAGE,
    LOTTERY_Sticker_REPLY_MESSAGE,
    LOTTERY_LOSE_REPLY_MESSAGE,
)
from filters import custom_filters
from libs.log import logger
from libs.state import state_manager
# === 目标贴纸集短名（必须是你创建的） ===
TARGET_STICKER_SET = "my_sticker_pack_by_xxxxx"

# === 默认 emoji ===
DEFAULT_EMOJI = "😄"


@Client.on_message(filters.me & filters.reply & filters.command("adds", prefixes="!"))
async def add_sticker_to_set(client, message):
    """
    使用示例：
        回复一张贴纸后发送：
        !addsticker 😎     → 使用 😎
        !addsticker         → 使用默认表情 😄
    """
    replied = message.reply_to_message

    if not replied or not replied.sticker:
        await message.reply("⚠️ 请回复一条贴纸消息再试。")
        return

    # 解析命令参数
    args = message.text.split(maxsplit=1)
    custom_emoji = args[1] if len(args) > 1 else None

    # emoji 选择逻辑
    emoji = (
        custom_emoji               # 用户自定义
        or replied.sticker.emoji   # 如果贴纸本身带 emoji
        or DEFAULT_EMOJI           # 否则用默认
    )

    # 下载贴纸文件
    file_path = await client.download_media(replied.sticker)
    # 上传文件到 Telegram 服务器
    uploaded_file = await client.save_file(file_path)

    try:
        # 调用 Telegram 原生 API 添加贴纸
        result = await client.invoke(
            functions.stickers.AddStickerToSet(
                stickerset=types.InputStickerSetShortName(short_name=TARGET_STICKER_SET),
                sticker=types.InputStickerSetItem(
                    document=uploaded_file,
                    emoji=emoji,
                    mask_coords=None,
                    keywords=[]
                )
            )
        )
        await message.reply(f"✅ 已添加贴纸到 `{TARGET_STICKER_SET}`，表情：{emoji}")
    except Exception as e:
        await message.reply(f"❌ 添加失败：\n`{e}`")
