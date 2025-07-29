# 标准库
import asyncio
import subprocess
from pathlib import Path

# 第三方库
from pyrogram import Client

# 自定义模块
from app import system_version_get
from config.config import API_HASH, API_ID, BOT_TOKEN, PT_GROUP_ID, proxy_set
from libs.log import logger


if proxy_set["proxy_enable"] == True:
    proxy = proxy_set["proxy"]
else:
    proxy = None


async def main():
    workdir_path = Path("sessions")
    workdir_path.mkdir(parents=True, exist_ok=True)
    user_app = Client(
        "user_account",
        api_id=API_ID,
        api_hash=API_HASH,
        workdir=str(workdir_path.resolve()),
        proxy=proxy,
        plugins=dict(root="user_scripts"),
    )
    bot_app = Client(
        "bot_account",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workdir=str(workdir_path.resolve()),
        proxy=proxy,
        plugins=dict(root="bot_scripts"),
    )
    project_name, tgbot_sate = await system_version_get()
    re_msg = f"您的{project_name} 项目已登录,本次为首次登录 状态如下:\n\n" + tgbot_sate
    async with user_app:

        await user_app.send_message(PT_GROUP_ID["BOT_MESSAGE_CHAT"], re_msg)
        logger.info("Mytgbot首次登录成功，登录信息创建成功")
        command = ["supervisorctl", "start", "main"]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("启动main成功")
        else:
            print(result.stdout)
            print(result.stderr)


if __name__ == "__main__":
    asyncio.run(main)
