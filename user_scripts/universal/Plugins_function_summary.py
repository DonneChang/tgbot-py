# 标准库
import asyncio
from pathlib import Path
from datetime import datetime

# 第三方库
from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.errors import Forbidden, FloodWait

# 自定义模块
from app import get_bot_app
from config.config import PT_GROUP_ID
from libs import others



mess_path = Path("temp_file/get_media")


@Client.on_message(filters.me & filters.command("re", prefixes=[",", "，"]))
async def forward_to_group(client: Client, message: Message):

    await message.delete()
    if reply := message.reply_to_message:
        try:
            # 获取重复次数，默认为1
            re_times = (
                int(message.command[1])
                if len(message.command) >= 2 and message.command[1].isdigit()
                else 1
            )
        except (IndexError, ValueError):
            # 捕获IndexError（当命令参数为空）和ValueError（当参数不是数字）并设置re_times为1
            re_times = 1
            await message.delete()

        for _ in range(re_times):
            try:
                # 如果聊天没有保护内容，执行转发
                await asyncio.sleep(0.3)
                if not message.chat.has_protected_content:
                    await reply.forward(
                        reply.chat.id, message_thread_id=reply.message_thread_id
                    )
                else:
                    # 否则执行复制操作
                    await reply.copy(
                        reply.chat.id,
                        message_thread_id=message.message_thread_id,
                    )
            except (Forbidden, FloodWait, Exception):
                return

    


@Client.on_message(filters.me & filters.command("getmsg", prefixes=[",", "，"]))
async def get_message(client: Client, message: Message):
    """
    获取消息信息
    """
    bot_app = get_bot_app()
    mess_path.mkdir(parents=True, exist_ok=True)
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
    if message.reply_to_message.text:
        file_name = f"{message.reply_to_message.text[:6]}_{current_time}.txt"
    else:
        file_name = f"{current_time}.txt"
    file_path = mess_path / file_name
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(message.reply_to_message))
    await bot_app.send_document(PT_GROUP_ID["BOT_MESSAGE_CHAT"], file_path)
    Path(file_path).unlink()
    await message.delete()


@Client.on_message(filters.me &  filters.command("id", prefixes=[",", "，"]))
async def get_id(client: Client, message: Message):
    """
    用户ID查询
    """
    re_mess = ""
    msg = message.reply_to_message or message
    chat_id = msg.chat.id

    if msg.from_user:
        re_mess = f"\nsender_chat id: {chat_id}\nuser id: {msg.from_user.id}\nusername: {msg.from_user.first_name}"
    elif msg.author_signature:
        re_mess = (
            f"\nsender_chat id: {chat_id}\nauthor_signature: {msg.author_signature}"
        )

    if re_mess:
        result = await message.edit(re_mess)
        await others.delete_message(result, 20)
    else:
        await others.delete_message(message, 1)


"""
@Client.on_message(
        filters.private 
        & filters.user(777000)
    )
async def forward_to_group(client:Client, message: Message):
    bot_app = get_bot_app()
    # 监听Telegram(777000)
        
    logger.info(f"Telegram(777000): {message.text}")
    await bot_app.send_message(PT_GROUP_ID['BOT_MESSAGE_CHAT'],message.text)
"""

# @Client.on_message(filters.me & filters.command("helpme"))
# async def help_message(client:Client, message: Message):
#     command_data = [
#     ("/id", "被回复的消息的telegram ID查询", "/id", "如果没有回复任何消息则查询自己的"),
#     ("/dme num", "删除当前群组num条自己发消息", "/dme 10", "删除当前群组10条自己发消息"),
#     ("/blockyword add str", "115群监听,增加不监听关键字", "/blockyword add 不良人", "新增不监听关键字 “不良人"),
#     ("/blockyword remove str", "115群监听,删除不监听关键字", "/blockyword remove 不良人", "删除不监听关键字 “不良人"),
#     ("/dyjk on/off", "115群电影监控 打开 / 关闭", "/dyjk on", "监听打开"),
#     ("/dyzf on/off", "CMSbot转发群消息打开/关闭", "/dyzf on", "转发打开"),
#     ("autochangename on/off", "telegram更新时间昵称打开/关闭", "/autochangename on", "打开"),
#     ("/zpr(zp) str num 0/1/2", "p站搜索二次图片(0 SFW 1 NSFW 2 混合)", "/zpr 明日香 2 0", "zpr图片模式/zp文件模式 命令后的参数可选"),
#     ("/jupai", "回复的文字消息或/jupai 文字 ", "/jupai 你好", "将‘你好’ 转为jupai"),
#     ("/xjj", "小姐姐视频", "/xjj", "/"),
#     ("/backuplist", "获取当前已有数据库备份清单", "/backuplist", "/"),
#     ("/dbrestore num", "还原第num号备份(num根据backuplist获取)", "/dbrestore 1", "还原第1个备份"),
#     ("/prizewheel num", "朱雀大转盘", "/prizewheel 10", "朱雀大转盘转10次"),
#     ("/getinfo", "朱雀查询个人信息", "/getinfo", "/"),
#     ("/fanda lose/win/all on/off", "朱雀打劫被打劫自动反击", "/fanda lose on", "被打劫输时自动反击启动")
# ]

#     command_imge = await generate_command_table_image(command_data)
#     reult_mess = await message.reply_photo(command_imge)
#     await message.delete()
