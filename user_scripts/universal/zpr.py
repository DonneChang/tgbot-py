# 标准库
import shutil
import contextlib
from pathlib import Path

# 第三方库
from httpx import AsyncClient
from pyrogram import filters, Client
from pyrogram.types import Message
from pyrogram.types import InputMediaPhoto, InputMediaDocument
from pyrogram.errors import RPCError

# 自定义模块
from libs.log import logger




pixiv_img_host = "i.pixiv.re"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.42"
}
data_path = Path("temp_file/zpr")

async def get_result(message, r18=0, num=3, size = "regular", tag=""):
    """
        # r18: 0为非 R18，1为 R18，2为混合（在库中的分类，不等同于作品本身的 R18 标识）
        # num: 图片的数量
        # size: 返回图片的尺寸质量
    """

    data_path.mkdir(parents=True, exist_ok=True)    
    des = "出错了，没有纸片人看了。"
 
    async with AsyncClient() as session:
        response = await session.get(
            f"https://api.lolicon.app/setu/v2?num={num}&r18={r18}&size={size}&tag={tag}",headers=headers,
            timeout=10,
            )
    if response.status_code != 200:
        logger.error(f"连接二次元大门出错。。。")
        return None
    await message.edit(f"..")  
    print(response)
    try:
        result = response.json()["data"]
    except Exception:
        logger.error(f"解析JSON出错。")
        return None
    print(result)
    setu_list_photo = []  # 发送
    setu_list_file = []  # 发送
    await message.edit(f"...")
    for i in range(len(result)):
        urls = result[i]["urls"][size].replace("i.pixiv.re", pixiv_img_host)
        img_name = f"{result[i]['pid']}_{i}.jpg"
        file_path = data_path / img_name
        try:
            async with AsyncClient() as get_immge:
                img = await get_immge.get(urls, headers=headers, timeout=10)                            
            if img.status_code != 200:
                continue
            with open(file_path, mode="wb") as f:
                f.write(img.content)
        except Exception:
            logger.error(f"连接二次元出错。。。")
            return None
        setu_list_photo.append(InputMediaPhoto(media=str(file_path),has_spoiler=True))
        setu_list_file.append(InputMediaDocument(media=str(file_path)))
    return setu_list_photo, setu_list_file, des if (setu_list_photo and setu_list_file) else None





@Client.on_message(
        filters.me
        & (filters.command("zpr", prefixes=[",", "，"])
        | filters.command("zp", prefixes=[",", "，"]))
    )
async def zpr(client: Client, message: Message):
 
    
    arguments = 0               # r18: 0为非 R18，1为 R18，2为混合
    number = 3                  # 图片数量
    immge_size = 'regular'      #图片的尺寸质量
    target = ""                 #模糊搜索目标

    commands = message.command
    args = commands[1:] if len(commands) > 1 else []
    args += [""] * (3 - len(args))  # 填充到4个参数，防止索引报错
    arg1, arg2, arg3 = args 

    target = arg1

    if arg2.isdigit():
        number = int(arg2)

    if commands[0] == 'zp':
        immge_size = 'original'

    if arg3.isdigit() and 0 <= int(arg3) <= 2:
        arguments = int(arg3)
    
    code_message = await message.edit(".")
    
    # 判断是否为 sed_file 模式
    sed_file = (commands[0] == 'zp')


    try:
        photoList,file_list, des = await get_result(message, arguments, number, immge_size, target)
        if not photoList:
            shutil.rmtree(data_path)
            return await message.edit(des)
        with contextlib.suppress(Exception):
            await message.edit("....")
        try:
            await client.send_media_group(
                message.chat.id,
                photoList,                
                reply_to_message_id=message.reply_to_message_id,
                )
            if sed_file:
                await client.send_media_group(
                    message.chat.id,
                    file_list,   
                    reply_to_message_id=message.reply_to_message_id,
                        )
        
        except RPCError as e:
            return await message.edit(
                "此群组不允许发送媒体。"
                if e.ID == "CHAT_SEND_MEDIA_FORBIDDEN"
                else f"发生错误：\n`{e}`"
                )   
    except Exception as e:
        logger.error(f"发生错误：\n`{e}`")
        return await message.edit(f"发生错误：\n`{e}`")    
    shutil.rmtree(data_path)
    await code_message.delete()
