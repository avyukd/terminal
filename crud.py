from data import *
from exceptions import *
from datetime import datetime
import os 
from utils import *

"""
Any interaction with data happens through this layer. 

to think about:
- how to do appends (append to notes, append to tags, etc) (ok if not efficient because rare?)
   i.e. prob just do read and update
"""

def add_ticker(ticker: str, tags: str, ql: bool, dd: bool, 
            pt: Optional[float], tev: Optional[float], notes: Optional[str]):
    ticker = ticker.upper()

    # check if duplicate ticker (use metadata db)  
    mdb = MetadataDB()
    ticker_list = mdb.get_all_tickers()

    if ticker in ticker_list:
        raise DuplicateException(f"{ticker} has already been added.")
    
    # check if valid ticker and get price
    lpa = LivePriceAPI()
    try:
        live_prices = lpa.get_live_price(ticker)
    except:
        raise InvalidTickerException(f"{ticker} is not a valid ticker.")

    price = live_prices["close"] 

    # timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # add historical data
    eoda = EodPriceAPI()
    df = eoda.get_eod_price(ticker)
    date_str = df.index[-1].strftime("%Y-%m-%d")
 
    df.to_csv(f"data/eod-prices/{ticker}.{date_str}.csv")

    # add to metadata db
    row = MetadataRow(ticker, tags, price, timestamp, ql, dd, pt, tev, notes)
    mdb.add_row(row)

    # add to tags.json
    ta = TagsAPI()
    ta.add_ticker_from_tagstring(ticker, tags)

def add_tickers_from_csv(path: str):
    # read csv 
    adds_df = pd.read_csv(path)
    ticker_list = adds_df["ticker"].tolist()

    mdb = MetadataDB()
    old_tickers = mdb.get_all_tickers()

    for ticker in ticker_list:
        if ticker in old_tickers:
            raise DuplicateException(f"{ticker} has already been added.")

    lpa = LivePriceAPI()
    try:
        live_prices = pd.DataFrame(lpa.get_live_prices(ticker_list))
    except:
        raise InvalidTickerException(f"One or more tickers are invalid.")
    
    # timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # add historical data
    eoda = EodPriceAPI()
    df = eoda.get_eod_prices(ticker_list)

    for ticker in ticker_list:
        date_str = df[ticker].index[-1].strftime("%Y-%m-%d")   
        df[ticker].to_csv(f"data/eod-prices/{ticker}.{date_str}.csv")

    columns = adds_df.columns
    for row in adds_df.itertuples():
        ticker = row.ticker
        tags = row.tags
        ql = row.ql if "ql" in columns else False
        dd = row.dd if "dd" in columns else False
        pt = row.pt if "pt" in columns else None
        tev = row.tev if "tev" in columns else None
        notes = row.notes if "notes" in columns else None
        price = live_prices.loc[live_prices["ticker"] == ticker, "close"].values[0]

        row = MetadataRow(ticker, tags, price, timestamp, ql, dd, pt, tev, notes)
        mdb.add_row(row)

    ta = TagsAPI()
    ta.add_tickers_from_tagstring(adds_df["ticker"].tolist(), adds_df["tags"].tolist())


def refresh_live_prices():
    # if None, refresh all
    # live prices stored in metadata.db

    mdb = MetadataDB()
    ticker_list = mdb.get_all_tickers()

    lpa = LivePriceAPI()
    live_prices = pd.DataFrame(lpa.get_live_prices(ticker_list))

    for row in live_prices.itertuples():
        ticker = row.ticker
        price = row.close
        mdb.update_row(ticker, {"price": price})

def refresh_eod_prices():
    tickers_to_fetch = []
    for fn in os.listdir("data/eod-prices"):
        ticker, date = fn_to_tokens(fn)
        if date < pd.Timestamp.today():
            tickers_to_fetch.append(ticker)
    
    # TODO: fix this -- refresh shouldn't just be going back one day lmao...
    # get one day before today timestamp
    sd = pd.Timestamp.today() - pd.Timedelta(days=1)
    eoda = EodPriceAPI()
    new_prices = eoda.get_eod_prices(tickers_to_fetch, start_date=sd)
    
    curr_prices = load_eod_prices()

    for ticker, data in new_prices.items():
        old_date_str = curr_prices[ticker].index[-1].strftime("%Y-%m-%d")
        date_str = data.index[-1].strftime("%Y-%m-%d")
        
        curr_prices[ticker] = pd.concat([curr_prices[ticker][:-1], data], ignore_index=False)

        curr_prices[ticker].to_csv(f"data/eod-prices/{ticker}.{date_str}.csv")
        if old_date_str != date_str:
            os.remove(f"data/eod-prices/{ticker}.{old_date_str}.csv")

def load_eod_prices(tickers: Optional[list[str]] = None) -> dict[str, pd.DataFrame]:
    prices = {}

    for file in os.listdir("data/eod-prices"):
        ticker, date = fn_to_tokens(file)

        if tickers is None or ticker in tickers:
            prices[ticker] = pd.read_csv(f"data/eod-prices/{file}", index_col=0)
            prices[ticker].index = pd.to_datetime(prices[ticker].index)

    return prices 

def delete_tickers(tickers: list[str]):
    mdb = MetadataDB()
    for ticker in tickers:
        mdb.delete_row(ticker)

    ta = TagsAPI()
    ta.delete_tickers(tickers)

    for fn in os.listdir("data/eod-prices"):
        for ticker in tickers:
            if fn.startswith(ticker):
                os.remove(f"data/eod-prices/{fn}")


def get_tickers_from_tagstring(tagstr: str) -> list[str]:
    ta = TagsAPI()
    return ta.get_tickers_from_tagstring(tagstr)

def update_ticker():
    # check if tags are being changed and update if needed
    pass

def update_all():
    # update eod data
    # update live prices
    # update excel price targets and tev 
    pass 