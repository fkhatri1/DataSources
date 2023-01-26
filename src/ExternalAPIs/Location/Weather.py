from ExternalAPIs.Location.Geocoding import MissingOpenWeatherAPIKey
import datetime
import requests
import os
from collections import namedtuple
from typing import List

Forecast = namedtuple("Forecast", 
                     ["datetime",
                      "description",
                      "temp",
                      "feels_like",
                      "cloud_cover_pct",
                      "precip_pct_chance",
                      "rainfall",
                      "snowfall",
                      "wind_speed",
                      "wind_gust",
                      "visibility"
                    ])

class Weather():
    def __init__(self):
        try:
            self.apikey = os.environ["OPEN_WEATHER_API_KEY"]
        except KeyError:
            raise MissingOpenWeatherAPIKey

    def get_five_day_forecast(self, lat:str, lon:str) -> List[Forecast]:
        url = "http://api.openweathermap.org/data/2.5/forecast"
        params = {
            "lat": lat,
            "lon": lon,
            "units": "imperial",
            "appid": self.apikey
        }

        r = requests.get(url, params).json()

        forecasts = []

        for f in r.get("list"):
            forecasts.append(Forecast(
                datetime.datetime.fromtimestamp(f.get("dt")),
                f.get("weather")[0].get("description"),
                round(f.get("main").get("temp")),
                round(f.get("main").get("feels_like")),
                f.get("clouds").get("all"),
                int(f.get("pop") * 100),
                round(f.get("rain", {}).get("3h", 0) * 0.0393701, 2), #convert to inches
                round(f.get("snow", {}).get("3h", 0) * 0.393701, 2), #convert to inches
                round(f.get("wind").get("speed")),
                round(f.get("wind").get("gust")),
                f.get("visibility")
            ))
            
        return forecasts
       
