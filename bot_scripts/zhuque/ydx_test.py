# 第三方库
from pyrogram import filters, Client
from pyrogram.types import Message

# 自定义模块
from config.config import MY_TGID
from libs import others
from libs.ydx_betmodel import test
from models.ydx_db_modle import Zhuqueydx
import numpy as np


@Client.on_message(filters.command("ydxtest") & filters.chat(MY_TGID))
async def zhuque_ydx_switch(client: Client, message: Message):
    count = int(message.command[1])
    reply_message = await message.reply("测试中...")
    data = await Zhuqueydx.get_data(website="zhuque", limit=count + 40)
    _data = np.array(data, dtype=int)
    _data = np.where(_data > 3, 1, 0)
    data = _data.tolist()
    models = test(data)
    r = "```\n"
    for k in models:
        r += f"模型{k}:\n历史失败次数:{models[k]["loss_count"]}\n最大失败轮次:{models[k]["max_nonzero_index"]}\n净胜次数:{models[k]["win_count"]}\n胜率:{models[k]["win_rate"]:.02%}\n当前失败轮次:{models[k]["turn_loss_count"]}\n模型预测:{models[k]["guess"]}\n\n"
    r += "```"
    # 赋值给模型同步
    await reply_message.edit(r)


@Client.on_message(filters.command("ydxclean") & filters.chat(MY_TGID))
async def ydxclean(client: Client, message: Message):
    await Zhuqueydx.remove_duplicate_records()
    await message.reply("清理完成")
