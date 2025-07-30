# 标准库
from datetime import datetime
from typing import Optional, Tuple

# 第三方库
from sqlalchemy import String, Integer, Numeric, DateTime, delete, func, desc, select
from sqlalchemy.orm import mapped_column, Mapped
import pandas as pd
import numpy as np

# 自定义模块
from models.database import Base
from models import async_session_maker


class Zhuqueydx(Base):
    """
    朱雀ydx 数据库
    """

    __tablename__ = "zhuque_ydx"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    website: Mapped[str] = mapped_column(String(32))
    die_point: Mapped[int] = mapped_column(Integer)
    lottery_result: Mapped[str] = mapped_column(String(32))
    consecutive_count: Mapped[int] = mapped_column(Integer)
    bet_side: Mapped[str] = mapped_column(String(32))
    bet_count: Mapped[int] = mapped_column(Integer)
    bet_amount: Mapped[float] = mapped_column(Numeric(16, 2))
    win_amount: Mapped[float] = mapped_column(Numeric(16, 2))

    @classmethod
    async def add_zhuque_ydx_result_record(
        cls,
        website: str,
        die_point: int,
        lottery_result: str,
        consecutive_count: int,
        bet_side: str,
        bet_count: int,
        bet_amount: float,
        win_amount: float,
    ):
        """
        ydx数据写入数据库

        参数:
            website (str): 网站名称
            die_point (int): 死点
            lottery_result (str): 开奖结果
            consecutive_side (str): 连续方向
            consecutive_count (int): 连续次数
            bet_amount (float): 投注金额
            win_amount (float): 中奖金额

        返回:
            None
        """
        async with async_session_maker() as session, session.begin():
            redpocket = cls(
                website=website,
                die_point=die_point,
                lottery_result=lottery_result,
                consecutive_count=consecutive_count,
                bet_side=bet_side,
                bet_count=bet_count,
                bet_amount=bet_amount,
                win_amount=win_amount,
            )
            session.add(redpocket)

    @classmethod
    async def get_latest_ydx_info(
        cls, website: str
    ) -> Optional[Tuple[str, int, int, float]]:
        """
        查询指定网站的最新一条记录的 lottery_result、consecutive_count、bet_count 和 win_amount。

        参数:
            website (str): 需要查询的站点标识。

        返回:
            Optional[Tuple[str, int, int, float]]: 如果存在记录，则返回对应字段的元组；
            否则返回 None。
        """
        async with async_session_maker() as session, session.begin():
            stmt = (
                select(
                    cls.lottery_result,
                    cls.consecutive_count,
                    cls.bet_count,
                    cls.win_amount,
                )
                .where(cls.website == website)
                .order_by(desc(cls.create_time))
                .limit(1)
            )
            result = (await session.execute(stmt)).one_or_none()
            if result:
                return result
            return None

    @classmethod
    async def get_data(
        cls, website: str = "zhuque", limit: int = 1
    ) -> Optional[Tuple[str, int, int, float]]:
        """
        查询指定网站的最新 limit 条 die_point 记录。

        参数:
            website (str): 需要查询的站点标识。
            limit (int): 查询的记录条数，默认为 1。

        返回:
            Optional[List[int]]: 如果存在记录，则返回 die_point 列表；
            否则返回 None。
        """
        async with async_session_maker() as session, session.begin():
            stmt = (
                select(
                    cls.die_point,
                )
                .where(cls.website == website)
                .order_by(desc(cls.create_time))
                .limit(limit)
            )
            result = (await session.execute(stmt)).scalars().all()
            if result:
                return result
            return None

    @classmethod
    async def remove_duplicate_records(cls):
        """
        删除create_time相同的重复记录，只保留每个create_time的最新记录(id最大的)
        """
        async with async_session_maker() as session, session.begin():
            # 子查询：找出每个create_time对应的最大id
            subq = (
                select(
                    cls.create_time,
                    func.max(cls.id).label("max_id")
                )
                .group_by(cls.create_time)
                .subquery()
            )

            # 删除不在子查询中的记录
            stmt = (
                delete(cls)
                .where(
                    cls.id.not_in(
                        select(subq.c.max_id)
                    )
                )
            )
            await session.execute(stmt)



def make_MACD(datas: pd.DataFrame, short=12, long=26, mid=9):
    ema1 = datas["close"].ewm((short - 1) / 2, adjust=False).mean()
    ema2 = datas["close"].ewm((long - 1) / 2, adjust=False).mean()
    dif = ema1 - ema2
    dea = dif.ewm((mid - 1) / 2, adjust=False).mean()
    macd = (dif - dea) * 2
    return macd


def make_KDJ(datas: pd.DataFrame, days=9, kn=3, dn=3):
    lowest = datas["low"].rolling(days).min()
    lowest = lowest.fillna(datas["low"].expanding().min())
    highest = datas["high"].rolling(days).max()
    lowest = lowest.fillna(datas["high"].expanding().max())
    rsv = (datas["close"] - lowest) / (highest - lowest) * 100
    rsv = rsv.fillna(100)
    k = rsv.ewm(kn - 1, adjust=False).mean()
    d = k.ewm(dn - 1, adjust=False).mean()
    j = 3 * k - 2 * d
    return pd.concat([k, d, j], axis=1)


class YdxStock(Base):
    __tablename__ = "ydx_stock"
    ydxid: Mapped[int] = mapped_column(Integer)
    close: Mapped[int] = mapped_column(Integer)
    high: Mapped[int] = mapped_column(Integer)
    low: Mapped[int] = mapped_column(Integer)
    K: Mapped[float] = mapped_column(Numeric(16, 2))
    D: Mapped[float] = mapped_column(Numeric(16, 2))
    J: Mapped[float] = mapped_column(Numeric(16, 2))
    MACD: Mapped[float] = mapped_column(Numeric(16, 2))

    # @classmethod
    # async def init(cls):
    #     # 获取Zhuqueydx表中最新记录的id
    #     async with async_session_maker() as session, session.begin():
    #         stmt = select(Zhuqueydx.id).order_by(desc(Zhuqueydx.create_time)).limit(1)
    #         result = (await session.execute(stmt)).scalar_one_or_none()
    #         ydxid = result + 1 if result else 1  # 如果没有记录则从1开始
            
    #     n = 2
    #     base_value = 1000
    #     cumulative_data = np.zeros_like(_data, dtype=float)
    #     cumulative_data[0] = base_value + _data[0]
    #     for i in range(1, len(_data)):
    #         cumulative_data[i] = cumulative_data[i - 1] + _data[i]
    #     num_windows = len(_data) // n
    #     windows = cumulative_data[: num_windows * n].reshape(-1, n)
    #     window_data = pd.DataFrame(
    #         {
    #             "close": windows[:, -1],  # Last cumulative value in each window
    #             "high": np.max(windows, axis=1),  # Max in each window
    #             "low": np.min(windows, axis=1),  # Min in each window
    #         }
    #     )
    #     macd = make_MACD(window_data)
    #     kdj = make_KDJ(window_data)
