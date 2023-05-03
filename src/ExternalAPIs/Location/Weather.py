from ExternalAPIs.Location.Geocoding import MissingOpenWeatherAPIKey
import datetime
import requests
import os
from collections import namedtuple
from typing import List, Callable, Tuple

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
    
    def get_three_day_forecast(self, lat:str, lon:str) -> List[Forecast]:
        five_day = self.get_five_day_forecast(lat, lon)
        return five_day[0:2]
    
    @staticmethod
    def get_criteria_function(criteria_name:str) -> Callable[[Forecast], Tuple[bool, float]]:
        def snow(f):
            if "snow" in f.description:
                return (True, f.snowfall)
            else:
                return (False, 0.0)
            
        def rain(f):
            if "rain" in f.description or "showers" in f.description:
                return (True, f.rainfall)
            else:
                return (False, 0.0)
            
        def hiking(f):
            hour = f.datetime.hour
            if hour < 6 or hour >= 18:
                return (False, 0.0)
            
            if f.temp < 30 or f.temp >= 85:
                return (False, 0.0)
            
            if f.feels_like < 30 or f.feels_like >= 85:
                return (False, 0.0)
            
            if f.wind_speed > 15:
                return (False, 0.0)
            
            return (True, 0.0)
                        
        matching_functions = {}
        matching_functions["snow"] = snow
        matching_functions["rain"] = rain
        matching_functions["hiking"] = hiking

        return matching_functions[criteria_name]
    
    @staticmethod
    def get_matching_periods(forecasts, criteria_name):
        matching_func = Weather.get_criteria_function(criteria_name)

        periods = []
        _start = None
        _end = None
        _amount = 0

        for i in range(len(forecasts)):
            curr = forecasts[i]
            curr_cond, curr_amount = matching_func(forecasts[i])
            prev_cond, _ = matching_func(forecasts[i-1])
            
            # first entry maches criteria
            if (i == 0 and curr_cond):
                _start = curr.datetime
                _amount = curr_amount
            # middle entry matches criteria, but prior does not (start of a new match period)
            elif(i != 0 and not prev_cond and curr_cond) :
                _start = curr.datetime
                _amount = curr_amount
            # continuing within a period
            elif _start is not None and curr_cond:
                _amount += curr_amount
            # ending a period in the middle of the set
            elif i != 0 and prev_cond and not curr_cond:
                _end = curr.datetime
                _amount += curr_amount
                periods.append((_start, _end, round(_amount, 2)))
                _start = None
                _end = None
                _amount = 0
            # ending a period at the end
            elif i == (len(forecasts) - 1) and curr_cond:
                _end = curr.datetime
                _amount += curr_amount
                periods.append((_start, _end, round(_amount, 2)))
                _start = None
                _end = None
                _amount = 0

        return periods
