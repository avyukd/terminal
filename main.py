# price when added? is the column that should be in db, not current price (that comes from live-prices.csv)


import argparse 
from crud import *
from views import *
from signals import *
from backtest import *

parser = argparse.ArgumentParser(description="Manage your intelligent watchlist.")

parser.add_argument('-ac', '--add_csv', nargs=1, help="Add tickers from your CSV file")

parser.add_argument('-at', '--add_ticker', nargs="+", 
                    help="Usage: <ticker> <tags> <ql> <dd> <pt> <tev> <notes*>. -1 to avoid pt/tev")

#TODO: shouldn't have to spec both
parser.add_argument('-r', '--refresh', nargs=1, help="Refresh prices. spec LIVE, EOD, or BOTH.")

parser.add_argument('-d', '--daily', action="store_true", help="Daily prices view.")
parser.add_argument('-pc', '--price_columns', nargs="*", help="Add price columns to view.")
parser.add_argument('-rnk', '--rank', nargs="+", help="Rank by column, ASC or DSC.")
parser.add_argument('-f', '--filter', nargs=1, help="Filter by tagstring.")
parser.add_argument('-hd', '--head', nargs=1, help="Head of view.")

parser.add_argument('-rm', '--remove',nargs="+", help="Remove tickers from your watchlist.")

parser.add_argument('-rd','--ret_dist',nargs="+", 
                    help="View returns distribution conditioned on price change over a window.\n Usage: <tickers/tagstring> <window_size> <dir: gt, lt, eq> <bound in %> <lookback (optional)>")
parser.add_argument('-lb', '--lookback', nargs=1, help="Lookback period.")
parser.add_argument('-b', '--bins', nargs=1, help="Bins for histogram.")

args = parser.parse_args()

if args.add_csv:
    path = args.add_csv[0]
    add_tickers_from_csv(path)
elif args.add_ticker:
    items = args.add_ticker
    if len(items) < 2:
        print ("Usage: <ticker> <tags> <ql> <dd> <pt> <tev> <notes*>")
        exit(1)
    
    ticker, tags = items[0], items[1]
    ql = bool(items[2]) if len(items) > 2 else False
    dd = bool(items[3]) if len(items) > 3 else False
    pt = float(items[4]) if (len(items) > 4 and items[4] != -1) else None
    tev = float(items[5]) if (len(items) >  5 and items[5] != -1) else None
    notes = "\n".join(items[6:]) if len(items) > 6 else None
    
    add_ticker(ticker, tags, ql, dd, pt, tev, notes)
elif args.daily:
    # default daily view settings: 
    # if args.tags:
    #     tags = args.tags
    # filter by tags and get list of tickers

    # pass into print daily view
    price_columns = None
    if args.price_columns:
        price_columns = args.price_columns

    rank_col = None
    rank_order = None
    if args.rank:
        if len(args.rank) > 2:
            print("Usage: <rank_col> <rank_order>")
            exit(1)
        rank_col = args.rank[0]
        rank_order = args.rank[1] if len(args.rank) > 1 else "DSC"
    
    tickers = None
    if args.filter:
        tagstr = args.filter[0]
        tickers = get_tickers_from_tagstring(tagstr)

    head = None
    if args.head:
        head = int(args.head[0])

    # TODO: check for out of bounds errors for price_columns
    print_daily_view(tickers=tickers, price_columns=price_columns,rank_col=rank_col,rank_order=rank_order,head=head)
elif args.remove:
    #TODO: functionize
    # rm from eod-prices
    delete_tickers(args.remove)
elif args.refresh:
    if args.refresh[0] == "LIVE":
        refresh_live_prices()
    elif args.refresh[0] == "EOD":
        refresh_eod_prices()
    elif args.refresh[0] == "BOTH":
        refresh_live_prices()
        refresh_eod_prices()
    else:
        print("Usage: LIVE, EOD, or BOTH")
        exit(1)
elif args.ret_dist:
    items = args.ret_dist
    if len(items) != 4:
        print("Usage: <tickers/tagstring> <window_size> <dir: gt, lt, eq> <bound in %>")
        exit(1)
    
    mdb = MetadataDB()
    all_tickers = mdb.get_all_tickers()

    ticker_or_tagstr_items = items[0].split(",")
    flag_tick = False
    for s in ticker_or_tagstr_items:
        if s in all_tickers:
            flag_tick = True
        if s not in all_tickers and flag_tick:
            print(f"Unrecognized ticker {s}.")
            exit(1)
    if flag_tick:
        tickers = ticker_or_tagstr_items
    else:
        tickers = get_tickers_from_tagstring(items[0])
    
    prices = load_eod_prices(tickers)
    window_size = items[1]
    direction = items[2]
    bound = float(items[3])
    if abs(bound) > 1:
        print("Bound will be treated as a percentage. For example, 0.05 is 5%.")

    lookback = None
    if args.lookback:
        lookback = args.lookback[0]
    
    bins = 20
    if args.bins:
        bins = int(args.bins[0])

    
    return_vals = get_return_distribution(tickers, prices, window_size, direction, bound, lookback)
    print("Number of samples:", len(return_vals))
    ab0 = sum([1 if x > 0 else 0 for x in return_vals])
    be0 = sum([1 if x < 0 else 0 for x in return_vals])
    print(f"Samples above 0: {ab0} ({ab0 / len(return_vals):.2%})")
    print(f"Samples below 0: {be0} ({be0 / len(return_vals):.2%})")
    print("Mean:", np.mean(return_vals).round(4))
    print("Std:", np.std(return_vals).round(4))

    #TODO: figure out how to plot y axis as probabilities rather than counts
    plot_histogram(return_vals, "Return Distribution", bins)

if __name__ == "__main__":
    ticker = "BTU"
    prices = load_eod_prices([ticker])
    df = rsi_zs(prices[ticker]["close"], 14, 2, 252)
    print_bt_summary(df, trade_window_days=10, lookback=252*5, hurdle=0)