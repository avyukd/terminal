# price when added? is the column that should be in db, not current price (that comes from live-prices.csv)


import argparse 
from crud import *
from views import *

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
