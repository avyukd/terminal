import pandas as pd
import numpy as np
import pandas_ta as pta
from scipy.stats import norm
import matplotlib.pyplot as plt

def get_moving_avg(ts: pd.Series, window: int):
    return ts.rolling(window=window).mean()

def get_rsi(ts: pd.Series, window: int):
    return pta.rsi(ts, period=window)

def get_z_score(ts: pd.Series, window=None, last=True):
    mean = ts.rolling(window=window).mean()
    std = ts.rolling(window=window).std()
    
    if last:
        if std.iloc[-1] == 0:
            return 0
        return (ts.iloc[-1] - mean.iloc[-1]) / std.iloc[-1]
    else:
        #TODO: solution for std == 0 in time series? 
        return (ts - mean) / std