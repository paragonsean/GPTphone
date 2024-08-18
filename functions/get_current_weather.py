import json

import aiohttp
import openmeteo_requests
import requests_cache
from Utils import log_function_call

@log_function_call
async def get_current_weather(latitude: float, longitude: float) -> str:
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    openmeteo = openmeteo_requests.Client(session=cache_session)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": latitude, "longitude": longitude, "current": "temperature_2m"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url=url, params=params) as response:
            data = await response.json()
            temperature = data['current']['temperature_2m']

            return json.dumps({"temperature": str(temperature)})