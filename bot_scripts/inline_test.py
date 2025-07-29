# 第三方库

import time
from pyrogram import Client
from pyrogram.types import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChosenInlineResult,
    InlineQuery,
    LinkPreviewOptions,
)
import numpy as np

# 自定义模块
from libs.ydx_betmodel import test
from models.ydx_db_modle import Zhuqueydx


async def calculate_ydx_results(count):
    data = await Zhuqueydx.get_data(website="zhuque", limit=count + 40)
    _data = np.array(data, dtype=int)
    _data = np.where(_data > 3, 1, 0)
    data = _data.tolist()
    models = test(data)

    r = f"测试{count}次结果:\n```\n"
    for k in models:
        r += f"模型{k}:\n历史失败次数:{models[k]['loss_count']}\n最大失败轮次:{models[k]['max_nonzero_index']}\n净胜次数:{models[k]['win_count']}\n胜率:{models[k]['win_rate']:.02%}\n当前失败轮次:{models[k]['turn_loss_count']}\n模型预测:{models[k]['guess']}\n\n"
    r += "```"
    return r


@Client.on_inline_query()
async def answer_inline_query(client, inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query.isdigit():
        results = [
            InlineQueryResultArticle(
                title="请输入测试数量",
                input_message_content=InputTextMessageContent(
                    "请输入要测试的数据数量(数字)"
                ),
                description="例如: 100 表示测试100条数据",
            )
        ]
    else:
        count = int(query)
        results = [
            InlineQueryResultArticle(
                id=f"{count}_{inline_query.from_user.id}_{int(time.time())}",
                title=f"测试 {count} 条数据",
                input_message_content=InputTextMessageContent(
                    f"准备测试 {count} 条数据，计算中",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                ),
                description="点击发送后开始计算",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("计算结果", callback_data="calculating")]]
                ),
            )
        ]
    print(f"回答内联查询: {results}")
    await inline_query.answer(results, cache_time=1)


@Client.on_chosen_inline_result()
async def on_chosen_inline_result(
    client: Client, chosen_inline_result: ChosenInlineResult
):
    if chosen_inline_result.result_id:
        try:
            count = int(chosen_inline_result.query)
            if chosen_inline_result.inline_message_id:
                await client.edit_inline_text(
                    inline_message_id=chosen_inline_result.inline_message_id,
                    text=await calculate_ydx_results(count),
                )
        except ValueError as e:
            print(f"处理内联结果时出错: {e}")
