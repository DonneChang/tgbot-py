"""
Telegram 贴纸转存脚本 (Pyrogram v2 完整兼容)
支持静态和动态贴纸的转存到自定义贴纸包
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Optional, Tuple

from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaDocument

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
    SITE_NAME = "stickers"
    DEFAULT_PACK_NAME = ""  # 如果空, 需要命令参数

    TEMP_DIR = Path("./temp_stickers")

    @classmethod
    def ensure_temp_dir(cls):
        cls.TEMP_DIR.mkdir(exist_ok=True)


# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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

            scale_size = Config.ANIMATED_SIZE if is_animated else Config.STATIC_SIZE
            scale_filter = f"scale='if(gt(iw,ih),{scale_size},-1)':'if(gt(iw,ih),-1,{scale_size})'"

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
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
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
# 文件清理管理
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
async def add_sticker(client: Client, message: Message):
    Config.ensure_temp_dir()
    cleanup = FileCleanup()
    DEFAULT_PACK_NAME = state_manager.get_item(Config.SITE_NAME.upper(), "pack_name")

    try:
        # 解析命令参数
        cmd_args = message.command[1:] if len(message.command) > 1 else []
        if not cmd_args and not DEFAULT_PACK_NAME:
            return await message.edit("❌ 请指定贴纸包名称: ,as <name> [emoji]")

        pack_name = cmd_args[0] if len(cmd_args) > 0 else DEFAULT_PACK_NAME
        emoji = cmd_args[1] if len(cmd_args) > 1 else Config.DEFAULT_EMOJI

        replied = message.reply_to_message
        if not replied:
            return await message.edit("❌ 请回复一张图片、贴纸或 GIF/视频")

        await message.edit(f"⏳ 正在处理媒体... (目标: `{pack_name}`)")

        # 下载媒体
        await message.edit("📥 正在下载媒体...")
        media_path = await client.download_media(replied)
        cleanup.add(media_path)
        if not media_path:
            return await message.edit("❌ 下载失败")

        # 判断是否动态贴纸
        is_animated = False
        if replied.sticker:
            is_animated = replied.sticker.is_animated or replied.sticker.is_video
        elif replied.animation or (replied.document and "video" in (replied.document.mime_type or "")):
            is_animated = True

        logger.info(f"检测到 {'动态' if is_animated else '静态'}媒体")

        # 转换格式
        await message.edit("🔄 正在转换格式...")
        converter = MediaConverter()
        processed_path = await converter.convert_to_sticker_format(media_path, is_animated)
        cleanup.add(processed_path)
        if not processed_path:
            return await message.edit("❌ 格式转换失败，请检查 FFmpeg")

        # 添加/创建贴纸包
        await message.edit("➕ 正在上传到 Telegram 并添加贴纸...")
        try:
            await client.add_sticker_to_set(
                user_id="me",
                name=pack_name,
                sticker=processed_path,
                emojis=emoji
            )
            await message.edit(f"✅ 成功添加到贴纸包 `{pack_name}`！")
        except Exception as e:
            # 如果贴纸包不存在,创建新贴纸包
            if "STICKERSET_INVALID" in str(e) or "STICKERSET_NOT_MODIFIABLE" in str(e):
                await client.create_new_sticker_set(
                    user_id="me",
                    name=pack_name,
                    title=pack_name,
                    sticker=processed_path,
                    emojis=emoji,
                    animated=is_animated
                )
                await message.edit(f"🆕 成功创建贴纸包 `{pack_name}` 并添加贴纸！")
            else:
                await message.edit(f"❌ 添加贴纸失败: {e}")
    except Exception as e:
        await message.edit(f"❌ 发生错误: {e}")
        logger.exception("处理贴纸时异常")
    finally:
        cleanup.cleanup()
