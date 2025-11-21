# 标准库
import asyncio
from datetime import datetime, timedelta

# 第三方库
import requests
from bs4 import BeautifulSoup
from pyrogram import filters, Client
from pyrogram.types import Message

# 自定义模块
from libs import others
from libs.log import logger
from libs.state import state_manager
from models.transform_db_modle import Transform

               
                         


SITE_NAME = "u2dmhy"
BONUS_NAME = "UCoin"


async def u2_dmhy_gift(recv_ID,amount,message): 
    cookie = state_manager.get_item(SITE_NAME.upper(),"cookie","")
    url = "https://u2.dmhy.org/mpshop.php"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh",
        "Cookie": cookie,
        "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }
    data = {
        'event': '1003',
        'recv': f'{recv_ID}',
        'amount': f'{amount}',
        'message': f'{message}',
    }
    try:
        # 发起请求
        with requests.post(url, headers=headers, data=data) as response:
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                result1 = soup.select_one("h2")
                if result1:
                    table = soup.select("table")
                    if table:
                        result2 = table[-1]
                        return True, f"{result1.get_text(strip=True)} ：\n    {result2.get_text(strip=True).split('。')[0]}"
                    else:
                        await Transform.add_transform_nouser(recv_ID, SITE_NAME, -float(amount))
                        return True, "无提示信息（无表格）"
                else:
                    await Transform.add_transform_nouser(recv_ID, SITE_NAME, -float(amount))
                    return True, "无提示信息（无 h2）"

            else:
                # HTTP 错误，不 raise 原始对象，直接用异常包装
                raise Exception(f"HTTP 请求失败，状态码：{response.status_code}")

    except Exception as e:
        logger.error(f"请求错误，{e}")
        return False, f"请求失败：{e}"




@Client.on_message(filters.me & filters.command(["u2", "u2s"], prefixes=[",", "，"]))
async def u2_dmhy_transform_pay(client: Client, message: Message):
    cmd = message.command
    command_name = cmd[0].lower()
    now = datetime.now()

    # 获取最新操作时间
    last_time = await Transform.get_latest_transform_createtime(SITE_NAME, "pay")
    if last_time:
        next_time = timedelta(minutes=5) - (now - last_time)
        seconds_to_sleep = max(next_time.total_seconds() + 2, 0)
    else:
        seconds_to_sleep = 300
    

    if command_name == "u2s":
        # 多人批量送糖
        if len(cmd) <= 3:
            reply = await message.edit("```\n命令格式错误，请输入 /u2s user1 user2 ... bonus message```")
            await others.delete_message(reply, 20)
            return

        user_list = cmd[1:-2]
        bonus = cmd[-2]
        note = cmd[-1]

        result_gift = ""
        status_message = await message.edit("```\nU2糖发射中···```")

        # 给第一个用户等待必要时间后发糖
        first_user = user_list[0]
        if seconds_to_sleep > 0:
            await asyncio.sleep(seconds_to_sleep)
        logger.info(f"正在赠送给: {first_user} {bonus} {BONUS_NAME}, 附言: {note}")
        success, detail = await u2_dmhy_gift(first_user, bonus, note)
        if success:
            result_gift += f"🎉 成功赠与 {first_user} 大佬 {bonus} {BONUS_NAME}\n"
        else:
            result_gift += f"❌ 赠与 {first_user} 的 {bonus} {BONUS_NAME} 失败: {detail or '未知原因'}\n"

        # 之后的用户每隔301秒发糖
        for username in user_list[1:]:
            await asyncio.sleep(301)
            logger.info(f"正在赠送给: {username} {bonus} {BONUS_NAME}, 附言: {note}")
            success, detail = await u2_dmhy_gift(username, bonus, note)
            if success:
                result_gift += f"🎉 成功赠与 {username} 大佬 {bonus} {BONUS_NAME}\n"
            else:
                result_gift += f"❌ 赠与 {username} 的 {bonus} {BONUS_NAME} 失败: {detail or '未知原因'}\n"            

        reply = await status_message.reply(f"```\n{result_gift}```")
        await others.delete_message(status_message, 90)
        await others.delete_message(reply, 90)

    else:
        # 单人发糖
        if len(cmd) != 4:
            reply = await message.edit("```\n命令格式错误，请输入 /u2 username bonus message```")
            await others.delete_message(reply, 20)
            return

        username, bonus, note = cmd[1], cmd[2], cmd[3]
        status_message = await message.edit("```\n幼儿糖发射中···```")

        if seconds_to_sleep > 0:
            await asyncio.sleep(seconds_to_sleep)

        logger.info(f"正在赠送给: {username} {bonus} {BONUS_NAME}, 附言: {note}")
        success, detail = await u2_dmhy_gift(username, bonus, note)
        if success:
            reply = await message.edit(f"```\n🎉 成功赠与 {username} 大佬 {bonus} {BONUS_NAME}```")
        else:
            reply = await message.edit(f"```\n❌ 赠与 {username} 的 {bonus} {BONUS_NAME} 失败\n原因: {detail}```")
        await others.delete_message(reply, 90)


