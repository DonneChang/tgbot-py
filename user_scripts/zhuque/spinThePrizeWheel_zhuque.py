# 标准库
import asyncio
import time

# 第三方库
import aiohttp
from pyrogram import filters, Client
from pyrogram.types import Message

# 自定义模块
from config.config import MY_TGID, PT_GROUP_ID
from libs import others
from libs.log import logger
from libs.state import state_manager
from user_scripts.zhuque.getInfo_zhuque import getInfo


SITE_NAME = "zhuque"

PRIZES = {
    1: "改名卡",
    2: "神佑7天卡",
    3: "邀请卡",
    4: "自动释放7天卡",
    5: "20G",
    6: "10G",
    7: "谢谢惠顾",
}
BONUS_VALUES = {1: 300000, 2: 100000, 3: 80000, 4: 30000}
API_URL = "https://zhuque.in/api/gaming/spinThePrizeWheel"

async def spin_wheel(draws: int, client: Client, message: Message):

    stats = {
        "cost": 0,
        "bonus_back": 0,
        "upload_in_gb": 0,
        "prize_counts": {k: 0 for k in PRIZES},
    }
    batch_size = 500
    tasks_count = int(state_manager.get_item("ZHUQUE", "prize_tasks", 4))

    lock = asyncio.Lock()
    start_time = time.time()
    async with aiohttp.ClientSession() as session:        
        for i in range(0, draws, batch_size):
            sub_draws = min(batch_size, draws - i)
            chunk = sub_draws // tasks_count
            extra = sub_draws % tasks_count
            tasks = [
                fetch_batch(chunk + (1 if j < extra else 0), session, stats, lock)
                for j in range(4)
            ]
            await asyncio.gather(*tasks)

            # 中途进度更新
            elapsed = time.time() - start_time
            cost = stats["cost"]
            bonus_back = stats["bonus_back"]
            gb = stats["upload_in_gb"]
            net_loss = (gb / 86.9863 * 10000) - (cost - bonus_back)
            efficiency = gb / max((cost - bonus_back), 1) * 10000
            summary = (
                "\n".join(
                    f"{PRIZES.get(k)} : {v}"
                    for k, v in stats["prize_counts"].items()
                    if v > 0
                )
                or "无"
            )
            await client.edit_message_text(
                message.chat.id,
                message.id,
                (
                    f"**抽奖进度：**\n"
                    f"已完成 {i + sub_draws}/{draws} 次  耗时：{elapsed:.3f} 秒\n"
                    f"**上传灵石比：** {efficiency:.2f} GB/万灵石\n"
                    f"按86.98 GB/万灵石计算净赚：{net_loss:.1f}\n\n"
                    f"耗费灵石 : **{cost}**\n"
                    f"道具回血 : **{int(bonus_back)}**\n"
                    f"获得上传 : **{gb} GB**\n\n"
                    f"**明细如下：**\n{summary}"
                ),
            )
    return stats


async def fetch_batch(count, session: aiohttp.ClientSession, stats, lock):
    cookie = state_manager.get_item(SITE_NAME.upper(),"cookie","")
    xcsrf = state_manager.get_item(SITE_NAME.upper(),"xcsrf","")
    headers = {
        "Cookie": cookie,
        "X-Csrf-Token": xcsrf,
    }
    for _ in range(count):
        try:
            async with session.post(API_URL, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"请求失败 status={resp.status}")
                    continue

                result = await resp.json()
                prize = int(result.get("data", {}).get("prize", -1))
                if prize == -1:
                    continue

                async with lock:
                    stats["prize_counts"][prize] += 1
                    stats["cost"] += 1500
                    if prize in BONUS_VALUES:
                        stats["bonus_back"] += BONUS_VALUES[prize] * 0.8
                    elif prize == 5:
                        stats["upload_in_gb"] += 20
                    elif prize == 6:
                        stats["upload_in_gb"] += 10
        except Exception as e:
            logger.exception(f"抽奖异常: {e}")


@Client.on_message(filters.me & filters.command("prizewheel", prefixes=[",", "，"]))
async def zhuque_ThePrizeWheel(client: Client, message: Message):
    try:
        if len(message.command) != 2 or not message.command[1].isdigit():
            return await send_usage_hint(client, message)

        count = int(message.command[1])
        info = await getInfo()
        available = int(info.get("bonus", 0))

        if count * 1500 > available:
            max_draw = available // 1500
            return await message.reply(
                f"```\n现有灵石不足，最多可抽奖 {max_draw} 次```",
            )
             
        waiting = await message.reply("```\n抽奖中……```")
        stats = await spin_wheel(count, client, waiting)
        
    except Exception as e:
        logger.exception("抽奖命令错误")
        await message.reply(f"发生异常: {e}")


async def send_usage_hint(message: Message):
    await message.reply(
        "```\n格式错误，请使用如下格式：\n/prizewheel 抽奖次数\n例如：/prizewheel 10```",
    )
