# 标准库
from abc import ABC, abstractmethod
import asyncio
import random

# 第三方库
import pandas as pd
import numpy as np

# 自定义
from app import logger
from models.ydx_db_modle import make_KDJ, make_MACD, Zhuqueydx


class BetModel(ABC):
    fail_count: int = 0
    guess_dx: int = -1

    @abstractmethod
    async def guess(self, data):
        """data 是 一个 40个数字的 01数组 最后一个是 最近发生的 0小1大"""
        pass

    async def test(self, data: list[int]):
        loss_count = [0 for _ in range(50)]
        turn_loss_count = 0
        win_count = 0
        total_count = 0
        for i in range(40, len(data) + 1):
            data_i = data[i - 40 : i]
            dx = await self.guess(data_i)
            if i < len(data):
                total_count += 1
                self.set_result(data[i])
                if data[i] == dx:
                    loss_count[turn_loss_count] += 1
                    win_count += 1
                    turn_loss_count = 0
                else:
                    turn_loss_count += 1
        max_nonzero_index = next(
            (
                index
                for index, value in reversed(list(enumerate(loss_count)))
                if value != 0
            ),
            -1,
        )
        return {
            "loss_count": loss_count[: max_nonzero_index + 1],
            "max_nonzero_index": max_nonzero_index,
            "win_rate": win_count / total_count,
            "win_count": 2 * win_count - total_count,
            "turn_loss_count": turn_loss_count,
            "guess": dx,
        }

    def set_result(self, result: int):
        """更新连败次数,在监听结果中调用了"""
        if self.guess_dx != -1:
            if result == self.guess_dx:
                self.fail_count = 0
            else:
                self.fail_count += 1

    def get_consecutive_count(self, data: list[int]):
        """
        根据秋人结果计算连大连小次数
        """
        if not data:
            return 0
        last = data[-1]
        count = 0
        for v in reversed(data):
            if v == last:
                count += 1
            else:
                break
        dx = "小大"
        logger.info(f"连{dx[last]} [{count}]次")
        return count

    def get_bet_count(self, data: list[int], start_count=0, stop_count=0):
        """根据配置计算当前下注多少次"""
        consecutive_count = self.get_consecutive_count(data)
        bet_count = consecutive_count - start_count
        if 0 <= bet_count < stop_count:
            return bet_count
        return -1

    def get_bet_bonus(self, start_bonus, bet_count):
        return start_bonus * (2 ** (bet_count + 1) - 1)


class A(BetModel):
    async def guess(self, data):
        self.guess_dx = 1 - data[-1]
        return self.guess_dx


class B(BetModel):
    async def guess(self, data):
        self.guess_dx = data[-1]
        return self.guess_dx

    def get_bet_count(self, data: list[int], start_count=0, stop_count=0):
        bet_count = self.fail_count - start_count
        if 0 <= bet_count < stop_count:
            return bet_count
        return -1


class E(BetModel):
    async def guess(self, data):
        if self.guess_dx == -1:
            self.guess_dx = random.randint(0, 1)
        if self.fail_count % 2 == 0:
            self.guess_dx = random.randint(0, 1)
        return self.guess_dx

    def get_bet_count(self, data: list[int], start_count=0, stop_count=0):
        bet_count = self.fail_count - start_count
        if 0 <= bet_count < stop_count:
            return bet_count
        return -1


class S(BetModel):
    async def guess(self, data):
        ydx_data = await Zhuqueydx.get_data(limit=200)
        _data = [1 if i > 3 else -1 for i in ydx_data]
        _data = _data[::-1]
        n = 2
        base_value = 1000
        cumulative_data = np.zeros_like(_data, dtype=float)
        cumulative_data[0] = base_value + _data[0]
        for i in range(1, len(_data)):
            cumulative_data[i] = cumulative_data[i - 1] + _data[i]
        num_windows = len(_data) // n
        windows = cumulative_data[: num_windows * n].reshape(-1, n)
        window_data = pd.DataFrame(
            {
                "close": windows[:, -1],  # Last cumulative value in each window
                "high": np.max(windows, axis=1),  # Max in each window
                "low": np.min(windows, axis=1),  # Min in each window
            }
        )
        kdj = make_KDJ(window_data)
        # logger.info(str(window_data))
        # 获取最后一个J-K和MACD值
        last_j = kdj.iloc[-1, 2]  # J是第三列
        last_k = kdj.iloc[-1, 0]  # K是第一列
        # logger.info(str(kdj))
        logger.info(f"J:{last_j:.02f}, K:{last_k:.02f}")
        if last_j >= last_k:
            return 1
        if last_j < last_k:
            return 0

    def get_bet_count(self, data: list[int], start_count=0, stop_count=0):
        return 0


models: dict[str, BetModel] = {"a": A(), "b": B(), "e": E(), "s": S()}


async def test(data: list[int]):
    data.reverse()
    ret = {}
    for model in models:
        ret[model] = await models[model].test(data)
    return ret
