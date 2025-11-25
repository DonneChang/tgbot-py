"""
Telegram 贴纸转存脚本
支持静态和动态贴纸的转存到自定义贴纸包
完全兼容 Pyrogram v2
"""

import os
import asyncio
import logging
from typing import Optional, Tuple
from pathlib import Path

from pyrogram import Client, filters, types
from pyrogram.errors import FloodWait
from pyrogram.raw.types import InputDocument, InputStickerSetItem, InputStickerSetShortName, InputUserSelf
from pyrogram.raw import functions

from libs.state import state_manager

# ============================================================
# 配置区域
# ============================================================
class Config:
    """脚本配置"""
    STATIC_SIZE = 512
    ANIMATED_SIZE = 512
    ANIMATED_FPS = 30
    ANIMATED_MAX_DURATION = 3
    ANIMATED_BITRATE = "256k"
    DEFAULT_EMOJI = "🤔"
    SITE_NAME = 'stickers'
    DEFAULT_PACK_NAME = ""
    TEMP_DIR = Path("./temp_stickers")

    @classmethod
    def ensure_temp_dir(cls):
        cls.TEMP_DIR.mkdir(exist_ok=True)


# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# 媒体转换模块
# ============================================================
class MediaConverter:

    @staticmethod
    async def convert_to_sticker_format(input_path: str, is_animated: bool = False) -> Optional[str]:
        try:
            output_ext = ".webm" if is_animated else ".png"
            output_path = str(Path(input_path).with_suffix("")) + "_processed" + output_ext

            scale_filter = (
                "scale='if(gt(iw,ih),{0},-1)':'if(gt(iw,ih),-1,{0})'".format(
                    Config.ANIMATED_SIZE if is_animated else Config.STATIC_SIZE
                )
            )

            if is_animated:
                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-vf", f"{scale_filter},fps={Config.ANIMATED_FPS}",
                    "-c:v", "libvpx-vp9",
                    "-b:v", Config.ANIMATED_BITRATE,
                    "-an",
                    "-t", str(Config.ANIMATED_MAX_DURATION),
                    "-auto-alt-ref", "0",
                    "-y", output_path
                ]
            else:
                cmd = ["ffmpeg", "-i", input_path, "-vf", scale_filter, "-y", output_path]

            logger.info(f"执行 FFmpeg 转换: {'动态' if is_animated else '静态'}贴纸")

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg 错误: {stderr.decode()}")
                return None

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"转换成功: {output_path}")
                return output_path

            logger.error("转换后文件不存在或为空")
            return None

        except Exception as e:
            logger.error(f"媒体转换异常: {e}")
            return None


# ============================================================
# 贴纸包管理模块
# ============================================================
class StickerManager:

    def __init__(self, client: Client):
        self.client = client

    async def detect_media_type(self, message: types.Message) -> Tuple[Optional[object], bool]:
        if message.sticker:
            return message.sticker, message.sticker.is_animated or message.sticker.is_video
        if message.animation:
            return message.animation, True
        if message.photo:
            return message.photo, False
        if message.document:
            doc = message.document
            mime = doc.mime_type or ""
            is_animated = "video" in mime or "gif" in mime
            return doc, is_animated
        return None, False

    async def upload_and_get_input_document(self, file_path: str) -> Optional[InputDocument]:
        """
        上传文件到 Telegram 并返回 InputDocument
        完全兼容 Pyrogram v2
        """
        try:
            uploaded = await self.client.upload_file(file_path)
            # Pyrogram v2 原生 raw 使用 InputDocument
            input_doc = InputDocument(
                id=uploaded.id,
                access_hash=uploaded.access_hash,
                file_reference=b"",
            )
            return input_doc

        except FloodWait as e:
            logger.warning(f"遇到 FloodWait,等待 {e.value} 秒")
            await asyncio.sleep(e.value)
            return await self.upload_and_get_input_document(file_path)
        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            return None

    async def add_to_sticker_set(self, pack_short_name: str, input_doc: InputDocument, emoji: str) -> Tuple[bool, str]:
        sticker_item = InputStickerSetItem(document=input_doc, emoji=emoji)
        try:
            await self.client.invoke(
                functions.stickers.AddStickerToSet(
                    stickerset=InputStickerSetShortName(short_name=pack_short_name),
                    sticker=sticker_item
                )
            )
            return True, f"✅ 成功添加到贴纸包！\nEmoji: {emoji}\nPack: `{pack_short_name}`"
        except Exception as e:
            error_msg = str(e)
            if "STICKERSET_INVALID" in error_msg:
                return False, "STICKERSET_INVALID"
            return False, f"❌ 添加失败: {error_msg}"

    async def create_sticker_set(
        self,
        pack_short_name: str,
        pack_title: str,
        input_doc: InputDocument,
        emoji: str,
        is_animated: bool
    ) -> Tuple[bool, str]:
        sticker_item = InputStickerSetItem(document=input_doc, emoji=emoji)
        try:
            await self.client.invoke(
                functions.stickers.CreateStickerSet(
                    user_id=InputUserSelf(),
                    title=pack_title,
                    short_name=pack_short_name,
                    stickers=[sticker_item],
                    animated=is_animated,
                    videos=is_animated
                )
            )
            return True, f"✅ 成功创建贴纸包并添加！\nEmoji: {emoji}\nPack: `{pack_short_name}`"
        except Exception as e:
            return False, f"❌ 创建贴纸包失败: {e}"


# ============================================================
# 文件清理工具
# ============================================================
class FileCleanup:

    def __init__(self):
        self.files_to_delete = []

    def add(self, file_path: Optional[str]):
        if file_path and os.path.exists(file_path):
            self.files_to_delete.append(file_path)

    def cleanup(self):
        for file_path in self.files_to_delete:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除文件失败 {file_path}: {e}")
        self.files_to_delete.clear()


# ============================================================
# 主处理逻辑
# ============================================================
@Client.on_message(filters.me & filters.reply & filters.command("adds", prefixes=[",", "，"]))
async def add_sticker(client: Client, message: types.Message):
    Config.ensure_temp_dir()
    cleanup = FileCleanup()
    DEFAULT_PACK_NAME = state_manager.get_item(Config.SITE_NAME.upper(), "pack_name")

    try:
        cmd_args = message.command[1:] if len(message.command) > 1 else []
        if not cmd_args and not DEFAULT_PACK_NAME:
            return await message.edit("❌ 请指定贴纸包名称: ,as <name> [emoji]")

        pack_short_name = (cmd_args[0] if len(cmd_args) > 0 else "") or DEFAULT_PACK_NAME
        emoji = cmd_args[1] if len(cmd_args) > 1 else Config.DEFAULT_EMOJI

        replied = message.reply_to_message
        if not replied:
            return await message.edit("❌ 请回复一张图片、贴纸或 GIF/视频")

        await message.edit(f"⏳ 正在处理媒体... (目标: `{pack_short_name}`)")

        manager = StickerManager(client)
        media, is_animated = await manager.detect_media_type(replied)
        if not media:
            return await message.edit("❌ 不支持的媒体类型")
        logger.info(f"检测到 {'动态' if is_animated else '静态'} 媒体")

        await message.edit("📥 正在下载媒体...")
        dl_path = await client.download_media(media)
        cleanup.add(dl_path)
        if not dl_path:
            return await message.edit("❌ 下载失败")

        await message.edit("🔄 正在转换格式...")
        converter = MediaConverter()
        processed_path = await converter.convert_to_sticker_format(dl_path, is_animated)
        cleanup.add(processed_path)
        if not processed_path:
            return await message.edit("❌ 格式转换失败,请检查 FFmpeg 是否正确安装")

        await message.edit("📤 正在上传到 Telegram...")
        input_doc = await manager.upload_and_get_input_document(processed_path)
        if not input_doc:
            return await message.edit("❌ 上传失败")

        await message.edit(f"➕ 正在添加到贴纸包 `{pack_short_name}`...")
        success, msg = await manager.add_to_sticker_set(pack_short_name, input_doc, emoji)
        if success:
            await message.edit(msg)
        elif msg == "STICKERSET_INVALID":
            await message.edit(f"🆕 贴纸包不存在,正在创建 `{pack_short_name}`...")
            success, msg = await manager.create_sticker_set(pack_short_name, pack_short_name, input_doc, emoji, is_animated)
            await message.edit(msg)
        else:
            await message.edit(msg)

    except FloodWait as e:
        await message.edit(f"⚠️ 触发频率限制,请等待 {e.value} 秒后重试")
        logger.warning(f"FloodWait: {e.value}s")
    except Exception as e:
        await message.edit(f"❌ 发生错误: {e}")
        logger.exception("处理贴纸时发生异常")
    finally:
        cleanup.cleanup()
