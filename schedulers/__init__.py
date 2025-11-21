# 第三方库
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 自定义模块
from libs.log import logger
from libs.state import state_manager


scheduler = AsyncIOScheduler()


from .zhuque.fireGenshinCharacterMagic import zhuque_autofire_firsttimeget
from .universal.auto_changename import auto_changename_temp
from .universal.ourbits import ourbits_send_msg

scheduler_jobs = {
    "autofire": zhuque_autofire_firsttimeget,
    "autochangename": auto_changename_temp,
    "ourbits_send_msg": ourbits_send_msg
}

async def start_scheduler():    
    for job in (schedulers := state_manager.get_section("SCHEDULER", {})):
        logger.info(f"Checking scheduler job: {job}")
        if schedulers[job] == "on" and job in scheduler_jobs:
            logger.info(f"Starting scheduler job: {job}")
            try:
                await scheduler_jobs[job]()  # 异步执行调度任务
            except Exception as e:
                logger.error(f"Failed to start job '{job}': {e}")


