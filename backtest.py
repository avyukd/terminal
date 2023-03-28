
import pandas as pd
from exceptions import *
from scipy.signal import argrelextrema
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional

required_columns = ["price", "feature", "signal"]

#TODO: lookback changed to like time period? like tuple of dates or sm
#TODO: division by zero errors
def print_bt_summary(df: pd.DataFrame, trade_window_days: int = 10, lookback: Optional[int] = None, hurdle: float = 0.20):
    # hurdle is hurdle IRR

    for col in required_columns:
        if col not in df.columns:
            raise InvalidDataFrameException(f"Column {col} not found in dataframe.")
    
    if lookback is not None:
        df = df[-lookback:]

    n = trade_window_days // 2

    df["min"] = np.nan
    df["max"] = np.nan
    df["fut_ret"] = np.nan

    df = df.reset_index()

    for i, row in df.iterrows():
        if row["signal"] == 1: # buy
            df.loc[i, "min"] = df.iloc[i-n:i+n]["price"].min()
        if row["signal"] == -1: # sell
            df.loc[i, "max"] = df.iloc[i-n:i+n]["price"].max()  

        if (row["signal"] == 1 or row["signal"] == -1) and i + trade_window_days < len(df):
            df.loc[i, "fut_ret"] = df.iloc[i+trade_window_days]["price"] / df.iloc[i]["price"] - 1
 

    buys = df[df["signal"] == 1]
    sells = df[df["signal"] == -1]

    buy_pct_errors = (buys["price"] / buys["min"] - 1).dropna().tolist()
    sell_pct_errors = (sells["max"] / sells["price"] - 1).dropna().tolist()

    buy_e = [abs(x) for x in buy_pct_errors]
    sell_e = [abs(x) for x in sell_pct_errors]
    total_e = buy_e + sell_e

    buy_avg_fut_ret = buys["fut_ret"].mean()
    sell_avg_fut_ret = sells["fut_ret"].mean()

    # win if fut_ret is a 20% IRR
    buy_wins = [1 if x * (252 / trade_window_days) >= hurdle else 0 for x in buys["fut_ret"].dropna().tolist()]
    sell_wins = [1 if -x * (252 / trade_window_days) >= hurdle else 0 for x in sells["fut_ret"].dropna().tolist()]
    buy_win_rate = sum(buy_wins) / len(buy_wins)
    sell_win_rate = sum(sell_wins) / len(sell_wins)
    win_rate = (sum(buy_wins) + sum(sell_wins)) / (len(buy_wins) + len(sell_wins))

    print("---Summary---")
    print("Basics:")
    print(f"\tTotal number of days: {len(df)}")
    print(f"\tNumber of buys: {len(buys)} ({len(buys)/len(df)*100:.2f}%)")
    print(f"\tNumber of sells: {len(sells)} ({len(sells)/len(df)*100:.2f}%)")
    print("Squared error:")
    print(f"\tBuy error: {sum(buy_e):.4f}")
    print(f"\tSell error: {sum(sell_e):.4f}")
    print(f"\tTotal error: {sum(total_e):.4f}")
    print("Average error:")
    print(f"\tBuy avg error: {sum(buy_e)/len(buy_e):.4f}")
    print(f"\tSell avg error: {sum(sell_e)/len(sell_e):.4f}")
    print(f"\tTotal avg error: {sum(total_e)/len(total_e):.4f}")
    print("Trade statistics:")
    print(f"\tBuy avg future return: {buy_avg_fut_ret:.4%}")
    print(f"\tSell avg future return: {sell_avg_fut_ret:.4%}")
    print(f"\tBuy win rate: {buy_win_rate:.4%}")
    print(f"\tSell win rate: {sell_win_rate:.4%}")
    print(f"\tTotal win rate: {win_rate:.4%}")

    df = df.set_index("date")
    df["price"].plot()

    buy_df = df[df["signal"] == 1]
    plt.scatter(buy_df.index, buy_df["price"], c="green")

    sell_df = df[df["signal"] == -1]
    plt.scatter(sell_df.index, sell_df["price"], c="red")

    plt.show()