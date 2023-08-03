from collections import namedtuple
import requests
import pandas as pd
import numpy as np
import pickle
import finnhub
import os
from datetime import date, datetime, timedelta
import logging
import json 

Profile = namedtuple("Profile", ['symbol', 'companyName', 'beta', 'div_pct', 'industry', 'website', 'description', 'sector', 'ipoDate', 'mktCap', 'volAvg'])
Earnings = namedtuple("Earnings", ['date', 'estimate', 'actual', 'surprise', 'surprise_pct'])

class Stock():
    def __init__(self):
        try:
            self.financialmodelingprep_key = os.environ["FINANCIAL_MODELING_PREP_KEY"]
        except KeyError:
            raise ValueError("FINANCIAL_MODELING_PREP_KEY not found.")
        try:
            self.finnhub_key = os.environ["FINNHUB_KEY"]
        except KeyError:
            raise ValueError("FINNHUB_KEY not found.")

    def get_historical_ohlc(self, symbol, start="2021-01-01", end=str(date.today())):
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
        params = {}
        params["apikey"] = self.financialmodelingprep_key
        params["from"] = start
        params["to"] = end
        try:
            r = requests.get(url, params).json()
            hist_json = r['historical']
        except Exception as e:
            logging.warn(f"Error occurred getting history of {symbol}.")
            raise e
        else:
            hist_df = pd.json_normalize(hist_json)
            hist_df = hist_df.drop(['adjClose', 'change', 'unadjustedVolume', 'changePercent', 'vwap', 'label', 'changeOverTime'], axis=1)
            hist_df = hist_df.sort_values('date', ascending=True)
            hist_df.set_index('date', drop=True, inplace=True)
            return hist_df

    def get_market_cap(self, symbol, _date=str(date.today())):
        url = f"https://financialmodelingprep.com/api/v3/historical-market-capitalization/{symbol}"
        params = {}
        params['apikey'] = self.financialmodelingprep_key
        params['limit'] = 1000
        r = requests.get(url, params)
        df = pd.json_normalize(r.json())
        df = df[df['date'] == _date]
        try:
            cap = int(df['marketCap'].values[0])
        except Exception as e:
            logging.warn(f"Could not get market cap for {symbol} on {_date}. Returning most current market cap.")
            profile = self.get_profile(symbol)
            cap = profile.mktCap
        return cap

    def get_profile(self, symbol):
        url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}"
        params = {}
        params['apikey'] = self.financialmodelingprep_key
        r = requests.get(url, params)
        try:
            _data=r.json()[0]

            return Profile( symbol = symbol,
                            companyName = _data['companyName'],
                            sector = _data['sector'],
                            industry = _data['industry'],
                            description = _data['description'],
                            mktCap = _data['mktCap'], 
                            beta = _data['beta'],
                            div_pct = round(100 * float(_data['lastDiv']) / float(_data['price']), 2),
                            ipoDate = _data['ipoDate'],
                            website = _data['website'],
                            volAvg = _data['volAvg']
                            )
        except Exception as e:
            logging.error(f"Could not get profile for {symbol}.")
            raise e


    def get_earnings_events(self, symbol, num_hist=4):
        url = f"https://financialmodelingprep.com/api/v3/historical/earning_calendar/{symbol}"
        params = {}
        params['apikey'] = self.financialmodelingprep_key
        params['limit'] = num_hist
        r = requests.get(url, params)
        df = pd.json_normalize(r.json())

        earnings_events = []
        for index, row in df.iterrows():
            try:
                earnings_events.append(
                    Earnings(
                        row['date'], 
                        row['epsEstimated'], 
                        row['eps'], 
                        round( float(row['eps']) - float(row['epsEstimated']), 2),
                        round(100 * ( float(row['eps']) - float(row['epsEstimated']) ) / float(row['epsEstimated']), 1 )
                    )
                )
            except Exception as e:
                raise e

        return earnings_events


    def get_next_earnings(self, symbol):
        today = date.today()
        next_year = today + timedelta(weeks=52)
        fhub = finnhub.Client(api_key=self.finnhub_key)
        _data = fhub.earnings_calendar(_from=str(today), to=str(next_year), symbol=symbol)
        _e = _data['earningsCalendar']
        return [Earnings(e['date'], 
                        e['epsEstimate'], 
                        e['epsActual'], 
                        None,
                        None) for e in _e]

    def get_earnings_string(self, symbol):
        return "\n".join(["date\t\test\tact\tsurp\tsurp %"]+[f"{x.date}\t{x.estimate}\t{x.actual}\t{x.surprise}\t{x.surprise_pct}" for x in self.get_earnings_events(symbol)])

    def get_profile_string(self, symbol):
        profile = self.get_profile(symbol)

        return f"""{profile.companyName} ({profile.symbol})
{profile.sector}, {profile.industry}

Market Cap: ${round(float(profile.mktCap) / 1_000_000_000, 2)}B
Dividend Yield: {profile.div_pct}%
Average Volume: {profile.volAvg}
Beta: {profile.beta}
IPO Date: {profile.ipoDate}

Upcoming and Recent EPS:
{API.get_earnings_string(symbol)}

{profile.website}
{profile.description}
"""

    def get_debt_to_book(self, symbol) -> float:
        url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{symbol}"
        params = {}
        params['apikey'] = self.financialmodelingprep_key
        params['period'] = "quarter"
        params['limit'] = 1
        r = requests.get(url, params)
        balance_sheet = r.json()[0]

        tangible_book_value = balance_sheet["totalAssets"] - balance_sheet["goodwillAndIntangibleAssets"] - balance_sheet["totalLiabilities"]
        total_debt = balance_sheet["totalDebt"]

        return total_debt / tangible_book_value

    def get_ratios(self, symbol):
        url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}"
        params = {}
        params['apikey'] = self.financialmodelingprep_key
        params['limit'] = 1
        r = requests.get(url, params)
        ratios = r.json()[0]

        return {"pe": ratios["peRatioTTM"], "dividend_yield": ratios["dividendYielPercentageTTM"]}

    def get_historical_cash_flow_statement(self, symbol) -> pd.DataFrame:
        url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{symbol}"
        params = {}
        params["period"] = "quarter"
        params["limit"] = 400
        params['apikey'] = self.financialmodelingprep_key
        r = requests.get(url, params)
        df = pd.json_normalize(r.json()).set_index(["date"])

        return df