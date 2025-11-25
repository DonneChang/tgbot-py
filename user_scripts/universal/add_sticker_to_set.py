"""
Telegram 贴纸转存脚本
支持静态和动态贴纸的转存到自定义贴纸包
"""

import os
import asyncio
import shlex
import subprocess
import logging
from typing import Optional, Tuple
from pathlib import Path

from pyrogram import Client, filters, raw, types
from pyrogram.errors import FloodWait

from libs.state import state_manager
# ============================================================
# 配置区域
# ============================================================
class Config:
    """脚本配置"""
    # FFmpeg 设置
    STATIC_SIZE = 512  # 静态贴纸尺寸
    ANIMATED_SIZE = 512  # 动态贴纸尺寸
    ANIMATED_FPS = 30  # 动态贴纸帧率
    ANIMATED_MAX_DURATION = 3  # 动态贴纸最大时长(秒)
    ANIMATED_BITRATE = "256k"  # 动态贴纸比特率
    
    # 默认 emoji
    DEFAULT_EMOJI = "🤔"
    
    # 默认贴纸包设置 (如果不想每次输入,可以在这里设置)
    # 留空则必须通过命令参数指定
    SITE_NAME = 'stickers'
    DEFAULT_PACK_NAME = ""  # 例如: "my_default_pack_by_yourname"
    
    # 临时文件目录
    TEMP_DIR = Path("./temp_stickers")
    
    @classmethod
    def ensure_temp_dir(cls):
        """确保临时目录存在"""
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
    """媒体文件转换器"""
    
    @staticmethod
    async def convert_to_sticker_format(
        input_path: str, 
        is_animated: bool = False
    ) -> Optional[str]:
        """
        将输入文件转换为符合 Telegram 贴纸标准的格式
        
        Args:
            input_path: 输入文件路径
            is_animated: 是否为动态贴纸
            
        Returns:
            转换后的文件路径,失败返回 None
        """
        try:
            output_ext = ".webm" if is_animated else ".png"
            output_path = str(Path(input_path).with_suffix("")) + "_processed" + output_ext
            
            # 构建缩放过滤器(长边 512px)
            scale_filter = (
                "scale='if(gt(iw,ih),{0},-1)':'if(gt(iw,ih),-1,{0})'"
                .format(Config.ANIMATED_SIZE if is_animated else Config.STATIC_SIZE)
            )
            
            if is_animated:
                # 动态贴纸: VP9 编码, 移除音频, 限制时长
                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-vf", f"{scale_filter},fps={Config.ANIMATED_FPS}",
                    "-c:v", "libvpx-vp9",
                    "-b:v", Config.ANIMATED_BITRATE,
                    "-an",  # 移除音频
                    "-t", str(Config.ANIMATED_MAX_DURATION),
                    "-auto-alt-ref", "0",  # 禁用备用参考帧(避免某些兼容性问题)
                    "-y", output_path
                ]
            else:
                # 静态贴纸: PNG 格式
                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-vf", scale_filter,
                    "-y", output_path
                ]
            
            logger.info(f"执行 FFmpeg 转换: {'动态' if is_animated else '静态'}贴纸")
            
            # 执行转换
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
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
    """贴纸包管理器"""
    
    def __init__(self, client: Client):
        self.client = client
    
    async def detect_media_type(
        self, 
        message: types.Message
    ) -> Tuple[Optional[object], bool]:
        """
        检测消息中的媒体类型
        
        Returns:
            (媒体对象, 是否为动态)
        """
        if message.sticker:
            return (
                message.sticker,
                message.sticker.is_animated or message.sticker.is_video
            )
        
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
    
    async def upload_and_get_input_document(
        self, 
        file_path: str
    ) -> Optional[raw.types.InputDocument]:
        """
        上传文件到 Saved Messages 并获取 InputDocument
        
        Args:
            file_path: 文件路径
            
        Returns:
            InputDocument 对象或 None
        """
        try:
            # 发送到自己的 Saved Messages
            saved_msg = await self.client.send_document(
                "me", 
                file_path, 
                force_document=True
            )
            
            doc = saved_msg.document
            input_doc = raw.types.InputDocument(
                id=doc.file_id,
                access_hash=doc.access_hash,
                file_reference=doc.file_reference
            )
            
            # 删除临时消息
            await saved_msg.delete()
            
            return input_doc
            
        except FloodWait as e:
            logger.warning(f"遇到 FloodWait,等待 {e.value} 秒")
            await asyncio.sleep(e.value)
            return await self.upload_and_get_input_document(file_path)
        
        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            return None
    
    async def add_to_sticker_set(
        self,
        pack_short_name: str,
        input_doc: raw.types.InputDocument,
        emoji: str
    ) -> Tuple[bool, str]:
        """
        添加贴纸到现有贴纸包
        
        Returns:
            (是否成功, 消息)
        """
        sticker_item = raw.types.InputStickerSetItem(
            document=input_doc,
            emoji=emoji
        )
        
        try:
            await self.client.invoke(
                raw.functions.stickers.AddStickerToSet(
                    stickerset=raw.types.InputStickerSetShortName(
                        short_name=pack_short_name
                    ),
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
        input_doc: raw.types.InputDocument,
        emoji: str,
        is_animated: bool
    ) -> Tuple[bool, str]:
        """
        创建新的贴纸包
        
        Returns:
            (是否成功, 消息)
        """
        sticker_item = raw.types.InputStickerSetItem(
            document=input_doc,
            emoji=emoji
        )
        
        try:
            await self.client.invoke(
                raw.functions.stickers.CreateStickerSet(
                    user_id=raw.types.InputUserSelf(),
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
    """文件清理管理"""
    
    def __init__(self):
        self.files_to_delete = []
    
    def add(self, file_path: Optional[str]):
        """添加待删除文件"""
        if file_path and os.path.exists(file_path):
            self.files_to_delete.append(file_path)
    
    def cleanup(self):
        """清理所有文件"""
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
    """处理添加贴纸命令"""
    Config.ensure_temp_dir()
    cleanup = FileCleanup()

    DEFAULT_PACK_NAME = state_manager.get_item(Config.SITE_NAME.upper(),"pack_name")
    
    try:
        # 1. 解析命令参数        
        cmd_args = message.command[1:] if len(message.command) > 1 else []
        if (not cmd_args and not DEFAULT_PACK_NAME):
            return await message.edit("❌ 请指定贴纸包名称: ,as <name> [emoji]")
        
        pack_short_name = (cmd_args[0] if len(cmd_args) > 0 else "") or DEFAULT_PACK_NAME
        emoji = cmd_args[1] if len(cmd_args) > 1 else Config.DEFAULT_EMOJI
        
        # 验证回复消息
        replied = message.reply_to_message
        if not replied:
            return await message.edit("❌ 请回复一张图片、贴纸或 GIF/视频")
        
        await message.edit(f"⏳ 正在处理媒体... (目标: `{pack_short_name}`)")
        
        # 2. 检测媒体类型
        manager = StickerManager(client)
        media, is_animated = await manager.detect_media_type(replied)
        
        if not media:
            return await message.edit("❌ 不支持的媒体类型")
        
        logger.info(f"检测到 {'动态' if is_animated else '静态'} 媒体")
        
        # 3. 下载媒体文件
        await message.edit("📥 正在下载媒体...")
        dl_path = await client.download_media(media)
        cleanup.add(dl_path)
        
        if not dl_path:
            return await message.edit("❌ 下载失败")
        
        # 4. 转换为贴纸格式
        await message.edit("🔄 正在转换格式...")
        converter = MediaConverter()
        processed_path = await converter.convert_to_sticker_format(dl_path, is_animated)
        cleanup.add(processed_path)
        
        if not processed_path:
            return await message.edit("❌ 格式转换失败,请检查 FFmpeg 是否正确安装")
        
        # 5. 上传并获取 InputDocument
        await message.edit("📤 正在上传到 Telegram...")
        input_doc = await manager.upload_and_get_input_document(processed_path)
        
        if not input_doc:
            return await message.edit("❌ 上传失败")
        
        # 6. 添加到贴纸包
        await message.edit(f"➕ 正在添加到贴纸包 `{pack_short_name}`...")
        success, msg = await manager.add_to_sticker_set(
            pack_short_name, 
            input_doc, 
            emoji
        )
        
        if success:
            await message.edit(msg)
        elif msg == "STICKERSET_INVALID":
            # 贴纸包不存在,创建新的
            await message.edit(f"🆕 贴纸包不存在,正在创建 `{pack_short_name}`...")
            success, msg = await manager.create_sticker_set(
                pack_short_name,
                pack_short_name,  # 使用相同的名称作为标题
                input_doc,
                emoji,
                is_animated
            )
            await message.edit(msg)
        else:
            await message.edit(msg)
    
    except FloodWait as e:
        await message.edit(f"⚠️ 触发频率限制,请等待 {e.value} 秒后重试")
        logger.warning(f"FloodWait: {e.value}s")
    
    except Exception as e:
        error_msg = f"❌ 发生错误: {str(e)}"
        await message.edit(error_msg)
        logger.exception("处理贴纸时发生异常")
    
    finally:
        # 清理临时文件
        cleanup.cleanup()
