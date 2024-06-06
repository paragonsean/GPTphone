import logging
import requests

logger = logging.getLogger(__name__)

async def get_current_weather(context, args):
    """
    Retrieves current weather data for a location.

    Args:
        context: The context object (not used in this function).
        args: A dictionary containing the location to retrieve the weather for.

    Returns:
        A string with the weather data or an error message.
    """
    location = args.get("location")
    if location is None:
        return "Please provide the location to retrieve the weather for."

    api_url = "https://weather.example.com/location"
    params = {"location": location}

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        weather_data = response.json()

        # Extract relevant weather information from the response
        temperature = weather_data.get("temperature")
        if temperature:
            return f"The current temperature in {location} is {temperature}°."
        else:
            return "Could not retrieve temperature information."

    except requests.RequestException as e:
        logger.error(f"Error retrieving weather data: {e}")
        return "Error retrieving weather data."
