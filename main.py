# 前置加速
import sys

# if sys.platform != "win32":
#     import uvloop

#     uvloop.install()

# 标准库
import asyncio

# 自定义模块
from app import start_app
from libs.watch_log import monitor_log_file


async def main():
    log_configs = {
        "log_file_path": "logs/main_err.log",
        "trigger_string": "Request timed out",
        "command": "supervisorctl restart main",
    }

    await asyncio.gather(start_app(), monitor_log_file(**log_configs))


if __name__ == "__main__":
    asyncio.run(main())
    print("Connected..", flush=True)
