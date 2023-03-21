import sqlite3
from typing import Optional
import eod
import ray
import pandas as pd
from utils import clean_adjust, clean_live_prices
import json
from exceptions import *

"""
Schema:
    CREATE TABLE metadata (
        ticker TEXT PRIMARY KEY, # eod ticker symbol
        tags TEXT, # comma separated list of tags, can be hierarchical
        price REAL, # latest price
        ql INTEGER, # quick look -- I have taken a quick look
        dd INTEGER, # deep dive -- I have done a deep dive
        pt REAL, # price target (fair value), optional
        tev REAL, # total enterprise value, USD mm, optional
        notes TEXT, # notes, optional
    )

Notes:
- Never use any of the below classes in a nested manner, because they could be optimized at a higher level...
"""

class MetadataRow:
    """
    For validation. Only when adding a new row. 
    """
    def __init__(self, ticker: str, tags: str, price: float, timestamp: str,
        ql: Optional[bool] = False, dd: Optional[bool] = False, 
        pt: Optional[float] = None, tev: Optional[float] = None, 
        notes: Optional[str] = None):
        
        self.ticker = ticker
        self.tags = tags
        self.price = price
        self.timestamp = timestamp

        self.ql = 1 if ql else 0
        self.dd = 1 if dd else 0
        self.pt = pt
        self.tev = tev
        self.notes = notes

    def get_tuple(self):
        return (self.ticker, self.tags, self.price, self.timestamp, self.ql, self.dd, self.pt, self.tev, self.notes)

class MetadataDB:
    def __init__(self):
        self.conn = sqlite3.connect('data/metadata.db')
        self.cursor = self.conn.cursor()

        # create if not exists
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                ticker TEXT PRIMARY KEY,
                tags TEXT,
                price REAL,
                timestamp TEXT,
                ql INTEGER, 
                dd INTEGER, 
                pt REAL,
                tev REAL,
                notes TEXT
            )
        ''')
    
    @staticmethod
    def get_row_from_tuple(row: tuple) -> MetadataRow:
        return MetadataRow(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8])

    def __del__(self):
        self.conn.close()

    def add_row(self, row: MetadataRow):
        self.add_rows([row])
    
    def add_rows(self, rows: list[MetadataRow]):
        self.cursor.executemany('INSERT INTO metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                [row.get_tuple() for row in rows])
        self.conn.commit()

    def get_row(self, ticker: str) -> tuple:
        return self.get_rows([ticker])[0]

    def get_rows(self, tickers: list[str]) -> list[tuple]:
        tickers = [f"'{ticker}'" for ticker in tickers]
        self.cursor.execute('SELECT * FROM metadata WHERE ticker IN ({})'.format(','.join(tickers)))
        return self.cursor.fetchall()

    def get_all_rows(self) -> list[tuple]:
        self.cursor.execute('SELECT * FROM metadata')
        return self.cursor.fetchall()
    
    def get_all_tickers(self) -> list[str]:
        self.cursor.execute('SELECT ticker FROM metadata')
        return [row[0] for row in self.cursor.fetchall()]

    def update_row(self, ticker: str, changes: dict):
        """dict must be a key value pair of columns and new values"""
        query = "UPDATE metadata SET {} WHERE ticker = '{}'".format(
            ', '.join(
                [f"{key} = '{value}'" if isinstance(value, str) else f"{key} = {value}" for key, value in changes.items()]
            ),
            ticker
        )
        self.cursor.execute(query)
        self.conn.commit()
    
    def delete_row(self, ticker: str):
        self.cursor.execute("DELETE FROM metadata WHERE ticker = '{}'".format(ticker))
        self.conn.commit()

class LivePriceAPI:
    def __init__(self):
        api_key = "6149ef1b322b37.04228930"
        self.client = eod.EodHistoricalData(api_key)

    @ray.remote
    def get_live_prices_helper(self, ticker: str) -> dict:
        return self.client.get_prices_live(ticker)
    
    def get_live_prices(self, tickers: list[str]) -> list[dict]:
        if not ray.is_initialized():
            ray.init()

        result_ids = []
        for ticker in tickers:
            result_ids.append(self.get_live_prices_helper.remote(self, ticker))
        
        live_results = ray.get(result_ids)
        return clean_live_prices(live_results)

    def get_live_price(self, ticker: str) -> dict:
        row = self.client.get_prices_live(ticker)
        return clean_live_prices([row])[0]

class EodPriceAPI:
    def __init__(self):
        api_key = "6149ef1b322b37.04228930"
        self.client = eod.EodHistoricalData(api_key)
    
    @ray.remote
    def get_eod_prices_helper(self, ticker: str, timestamp: Optional[pd.Timestamp]) -> tuple[str, pd.DataFrame]:
        if timestamp is None:
            data = pd.DataFrame(self.client.get_prices_eod(ticker))
        else:
            data = pd.DataFrame(self.client.get_prices_eod(ticker, from_=timestamp))
        return (ticker, data)

    def get_eod_prices(self, tickers: list[str], start_date: Optional[pd.Timestamp] = None) -> dict[str, pd.DataFrame]:
        if not ray.is_initialized():
            ray.init()
        
        result_ids = []
        for ticker in tickers:
            result_ids.append(self.get_eod_prices_helper.remote(self, ticker, start_date))
        
        results = ray.get(result_ids)

        prices = {}
        for (ticker, data) in results:
            try:
                prices[ticker] = clean_adjust(data)
            except KeyError as e:
                print(f"Error loading {ticker}: {e}")

        return prices

    def get_eod_price(self, ticker: str, start_date: Optional[pd.Timestamp] = None) -> pd.DataFrame:
        if start_date is None:
            data = pd.DataFrame(self.client.get_prices_eod(ticker))
        else:
            data = pd.DataFrame(self.client.get_prices_eod(ticker, from_=start_date))
        
        try:
            return clean_adjust(data)
        except KeyError as e:
            raise InvalidTickerException(f"Error loading EOD prices for {ticker}: {e}")

class TagsAPI:
    def __init__(self):
        with open('data/tags.json', 'r') as f:
            self.tags_json = json.load(f)
        self.write_flag = False

    def __del__(self):
        if self.write_flag:
            with open('data/tags.json', 'w') as f:
                json.dump(self.tags_json, f, indent=4)

    def add_tickers_from_tagstring(self, tickers: list[str], tagstrings: list[str]):
        for ticker, tagstring in zip(tickers, tagstrings):
            self.add_ticker_from_tagstring(ticker, tagstring)

    def add_ticker_from_tagstring(self, ticker: str, tagstring: str):
        tagpaths = tagstring.split(',')
        for tagpath in tagpaths:
            p = tagpath.split("/")
            level = self.tags_json
            for tag in p:
                if tag not in level:
                    level[tag] = {}
                level = level[tag]
            if 'tickers' not in level:
                level['tickers'] = []
            if ticker not in level['tickers']:
                level['tickers'].append(ticker)
        
        self.write_flag = True
    
    def get_tickers_from_tagstring(self, ts: str) -> list[str]:
        paths = ts.split(",")
        all_tickers = []

        for path in paths:
            p = path.split("/")
            level = self.tags_json
            
            for tag in p:
                if tag not in level:
                    raise TagPathNotFoundException(f"Tag {tag} not found in {path}")
                level = level[tag]

            stack = [level]
            while len(stack) > 0:
                level = stack.pop()
                for tag in level:
                    if tag == 'tickers':
                        all_tickers.extend(level[tag])
                    else:
                        stack.append(level[tag])
        
        return all_tickers

    def delete_tickers(self, tickers: list[str]):
        # iterate using dfs, delete tickers from all tags
        stack = [self.tags_json]
        while len(stack) > 0:
            level = stack.pop()
            for tag in level:
                if tag == 'tickers':
                    for ticker in tickers:
                        if ticker in level[tag]:
                            level[tag].remove(ticker)
                else:
                    stack.append(level[tag])

                
            