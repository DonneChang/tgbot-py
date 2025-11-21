# 标准库
import asyncio
import time
from typing import Optional, Tuple
from datetime import datetime, timedelta, date

# 第三方库
import aiohttp

# 自定义模块
from libs.log import logger
from libs.state import state_manager
from models.redpocket_db_modle import Redpocket
from schedulers import scheduler


trgatid = -4200814739
TRGATID = -1001726902866
#@scheduler.scheduled_job("cron", hour="0,3,6,9,12,15,18,21", minute="0", second="0", id="ourBits_send_messages")

#async def ourbits_seed_messges():
#    await app.send_message(trgatid,f"祝贺OurBits八周年快乐")


@scheduler.scheduled_job("cron", hour="2,5,8,11,14,19,20,21", minute="57", second="59", id="ourbits_send_msg")

async def ourbits_send_msg():
    from app import get_user_app
    user_app = get_user_app()
    i = 0
    start_time = time.time()
    while i< 316180000:     
        i+=1
    await user_app.send_message(trgatid,f"祝贺OurBits八周年快乐")
