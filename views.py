from crud import *
from data import *
from tabulate import tabulate
import numpy as np 
import matplotlib.pyplot as plt
import seaborn as sns

default_price_columns = [
    "0d", "1w", "3m", "1y" 
]

# does live vs. eod price -- should be fixed bc would be 0 after hours unless u change to 1d lookback

def print_daily_view(tickers: Optional[list[str]] = None, price_columns: Optional[list[str]] = None, 
                     rank_col: Optional[str] = None, rank_order: Optional[str] = None, head: int = None):
    # default to showing all tickers
    # head = show only top n movers -- could also be negative maybe instead of tail?? 
    # tail = show only bottom n movers 
    # signals are based on EOD, so not included here -- only want stuff based on live price!
    # can also have live price vs price target
    # remember live prices should be pulled from the DB -- not the API!! updatel live can be separate function
    
    mdb = MetadataDB()
    if tickers is None:
        tickers = mdb.get_all_tickers()

    metadata = mdb.get_rows(tickers)
    prices = load_eod_prices(tickers)

    if price_columns is None:
        price_columns = default_price_columns

    price_columns = [col.lower() for col in price_columns]

    if "def" in price_columns:
        price_columns.remove("def")
        price_columns += default_price_columns

    #TODO: figure out better way to do ytd / other non-day based ranking
    if "ytd" in price_columns:
        price_columns.remove("ytd")
        ytd_days = (datetime.now() - datetime(datetime.now().year, 1, 1)).days
        ytd_trading_days = (252/365) * ytd_days
        price_columns.append(f"{ytd_days}d")

    # TODO: fix this to use calendar dates
    code_to_days = {'d': 1, 'w' : 5, 'm': 20, 'y': 252}
    int_price_columns = [int(col[:-1]) * code_to_days[col[-1]] for col in price_columns]

    table = []
    for row in metadata:
        view_row = []

        metadata_row = MetadataDB.get_row_from_tuple(row)
        ticker, tags, price = metadata_row.ticker, metadata_row.tags, metadata_row.price

        # check if price is float
        try:
            price = float(price)
        except:
            price = np.nan

        view_row += [ticker, tags, price]

        for lookback in int_price_columns:
            #TODO: more elegant solution
            if np.isnan(price):
                change = np.nan
            else:
                change = price / prices[ticker].iloc[-min(lookback+1, len(prices[ticker]))].close - 1
            view_row.append(change)
        table.append(view_row)

    df = pd.DataFrame(table, columns=["ticker", "tags", "price"] + price_columns)

    if rank_col is not None:
        df = df.sort_values(by=rank_col, ascending=rank_order == "ASC")

    for col in price_columns:
        # df[col] *= 100
        df[col] = df[col].astype(float).map("{:.1%}".format)

    df["price"] = df["price"].astype(float).map("{:.2f}".format)

    df = df.head(head) if head is not None else df
    
    print(tabulate(df, headers='keys', tablefmt='psql', showindex=False))

def plot_histogram(vals: list[float], title: str, bins: int = 20):
    # show probabilities not counts
    sns.displot(vals, kde=True, bins=bins)
    plt.show()