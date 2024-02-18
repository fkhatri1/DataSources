import json
from datetime import date, datetime, timedelta
from typing import List
import pandas as pd
import requests
import logging
import os
from collections import namedtuple

ScreeningCriteria = namedtuple("ScreeningCriteria", [
    "country",
    "min_market_cap",
    "min_volume",
    "min_dividend",
    "max_beta",
    "is_etf",
    "is_actively_trading"
])

ScreeningResult = namedtuple("ScreeningResult", [
    "symbol",
    "company_name",
    "market_cap",
    "sector",
    "beta",
    "last_annual_dividend",
    "volume",
    "exchange"
])

class Screener():
    def __init__(self) -> None:
        try:
            self.apikey = os.environ["FINANCIAL_MODELING_PREP_KEY"]
        except KeyError:
            raise MissingFinancialModelingPrepAPIKey

    def screen(self, criteria: ScreeningCriteria) -> List[ScreeningResult]:         
            #api call to financialmodelingprep stock screener 
            url = f"https://financialmodelingprep.com/api/v3/stock-screener"
            params = {}
            params["limit"] = 50000
            if criteria.country is not None:
                params['country'] = criteria.country
            if criteria.min_market_cap is not None:
                params['marketCapMoreThan'] = criteria.min_market_cap
            if criteria.max_beta is not None:
                params['betaLowerThan'] = criteria.max_beta
            if criteria.min_volume is not None:
                params['volumeMoreThan'] = criteria.min_volume
            if criteria.min_dividend is not None:
                params['dividendMoreThan'] = criteria.min_dividend
            if criteria.is_etf is not None:
                params['isEtf'] = criteria.is_etf
            if criteria.is_actively_trading is not None:
                params['isActivelyTrading'] = criteria.is_actively_trading

            params['apikey'] = self.apikey
            #params['exchange'] = "NASDAQ,NYSE"
            params['betaMoreThan'] = 0.9

            result_set_raw = requests.get(url, params).json()
            result_set = []
            for result in result_set_raw:
                result_set.append(ScreeningResult(
                    result["symbol"],
                    result["companyName"],
                    result["marketCap"],
                    result["sector"],
                    result["beta"],
                    result["lastAnnualDividend"],
                    result["volume"],
                    result["exchangeShortName"]
                ))

            logging.info(f'Screening has selected {len(result_set)} candidate symbols.')

            return result_set

    def deep_value_screen(self):
        import ExternalAPIs.Finance.Reference as ref
        import ExternalAPIs.Finance.Stock as stock

        dv_screen_criteria = ScreeningCriteria(
            country = "US",
            min_market_cap = 1_000_000_000,
            min_volume = 100,
            min_dividend = 0.01,
            max_beta = None,
            is_etf = False,
            is_actively_trading = True
        )
        candidates = self.screen(dv_screen_criteria)

        r = ref.Reference()
        s = stock.Stock()

        aaa_yield = r.corporate_aaa_yield()

        results = set()
        for c in candidates:
            try:
                _ratios = s.get_ratios(c.symbol)
                earnings_yield = 1.0 / _ratios["pe"]
                dividend_yield = _ratios["dividend_yield"]
                debt_to_book = s.get_debt_to_book(c.symbol)

                if (earnings_yield / 2.5 >= aaa_yield) and (dividend_yield * 2.5 / 3.0 >= aaa_yield) and (debt_to_book >= 0) and (debt_to_book < 0.9):
                    trimmed_symbol = c.symbol.split("-")[0]
                    results.add(trimmed_symbol)
                    print(f"{trimmed_symbol} - {c.company_name}")
            except Exception as e:
                print(e)
                continue

        return results
