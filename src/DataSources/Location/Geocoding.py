import requests
import os
from typing import Tuple

class MissingOpenWeatherAPIKey(Exception):
    """Open Weather API Key Missing. Expecting key in env var OPEN_WEATHER_API_KEY."""
    pass

class CouldNotFindLocation(Exception):
    """Could not resolve location."""
    pass

class InvalidResponse(Exception):
    """Invalid Response from Open Weather API."""
    pass

class Geocoder():
    def __init__(self):
        try:
            self.apikey = os.environ["OPEN_WEATHER_API_KEY"]
        except KeyError:
            raise MissingOpenWeatherAPIKey
        
    def get_coordinates(self, loc: str) -> Tuple[str, str]:
        url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {
            "q": loc,
            "limit": 1,
            "appid": self.apikey
        }
        try:
            r = requests.get(url, params).json()
        except Exception:
            raise InvalidResponse
        try:
            res = r[0]
        except IndexError:
            raise CouldNotFindLocation
        return (res.get("lat"), res.get("lon"))