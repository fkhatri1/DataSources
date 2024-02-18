import json
from datetime import date, datetime, timedelta
from typing import List
import pandas as pd
import requests
import logging
import os
from collections import namedtuple

class Reference():
    def __init__(self) -> None:
        try:
            self.apikey = os.environ["NASDAQ_DATA_LINK_KEY"]
        except KeyError:
            raise ValueError("NASDAQ_DATA_LINK_KEY not found.")

    def corporate_aaa_yield(self) -> float:
        url = "https://data.nasdaq.com/api/v3/datasets/ML/AAAEY.json"
        params = {"rows": 1, 'api_key': self.apikey}

        result_set_raw = requests.get(url, params).json()
        result = result_set_raw["dataset"]["data"][0][1]

        return result / 100
