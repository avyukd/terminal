
from typing import Optional
from exceptions import *
import pandas as pd
from signal_utils import *

def get_return_distribution(tickers: list[str], prices: dict, window_size: str, dir: str, bound: float, lookback: Optional[int]=None):
    # TODO: functionize so there is no code duplication
    code_to_days = {'d': 1, 'w' : 5, 'm': 20, 'y': 252}
    window_size = int(window_size[:-1]) * code_to_days[window_size[-1]]
    if lookback is not None:
        lookback = int(lookback[:-1]) * code_to_days[lookback[-1]]
    
    dis_values = []

    for ticker in tickers:
        if len(prices[ticker]) < window_size:
            continue

        if lookback is not None:
            t_prices = prices[ticker]["close"][-lookback:]
        else:
            t_prices = prices[ticker]["close"]
        
        windows = [t_prices[i:i+window_size+1] for i in range(0, len(t_prices), window_size)]

        windowed_returns = []
        for window in windows:
            windowed_returns.append( (window[-1] / window[0]) - 1)

        def check_condition(x, dir_str, bound):
            if dir_str == "gt":
                return x > bound
            elif dir_str == "lt":
                return x < bound
            elif dir_str == "eq":
                return x == bound
            else:
                raise InvalidDirectionString("dir_str must be 'gt' 'lt' or 'eq'")

        for i in range(1, len(windowed_returns)):
            if check_condition(windowed_returns[i - 1], dir, bound):
                dis_values.append(windowed_returns[i])
        
    return dis_values


# ts, feature, signal, strength? 

def rsi_zs(ts: pd.Series, window_size: int = 14, threshold: float = 2, zs_lookback: int = 252) -> pd.DataFrame:
    """
    ts is a pandas series indexed by date and containing price data 
    decreasing window size makes it more sensitive to recent price changes, and thus more likely to trigger a signal
    threshold is the number of standard deviations away from the mean that the RSI must be to trigger a signal
    """
    df = pd.DataFrame()
    df["price"] = ts

    rsi_ts = get_rsi(ts, window_size)
    df["feature"] = get_z_score(rsi_ts, zs_lookback, last=False)
    df["signal"] = df["feature"].apply(lambda x: -1 if x > threshold else 1 if x < -threshold else 0)
    
    return df