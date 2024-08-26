import json
import aiohttp
import openmeteo_requests
import requests_cache
from Utils import log_function_call, configure_logger

logger = configure_logger(__name__)
async def get_current_weather( latitude: float, longitude: float) -> str:
    logger.warning(f"inside get_current_weather")
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": latitude, "longitude": longitude, "current": "temperature_2m"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url=url, params=params) as response:
            data = await response.json()
            temperature = data['current']['temperature_2m']
            return json.dumps({"temperature": str(temperature)})
