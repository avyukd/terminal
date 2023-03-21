import pandas as pd 

def clean_adjust(data) -> pd.DataFrame:
    data.index = pd.to_datetime(data['date'])
    data.drop(columns = ['date'], inplace = True)

    ratio = data['close'] / data['adjusted_close']
    for col in ['open', 'high', 'low', 'close']:
        data[col] /= ratio
    return data

def clean_live_prices(live_results: list[dict]) -> list[dict]:
    clean_results = []
    for result in live_results:
        if result["code"].endswith("US"):
            result["code"] = result["code"].split(".")[0]
        result["ticker"] = result.pop("code")
        clean_results.append(result)
    return clean_results        

def fn_to_tokens(fn) -> tuple[str, pd.Timestamp]:
    tokens = fn.split(".")
    ticker = ".".join(tokens[:-2])
    date = pd.Timestamp(tokens[-2])
    return (ticker, date)