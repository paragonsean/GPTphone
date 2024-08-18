import os

import requests

api_key = os.getenv('TICKET_MASTER_API_KEY')  # Retrieve API key from environment variable

'''
Author: Sean Baker
Date: 2024-07-21
Description: API to search for venues 
'''
def search_events(api_key, params):
    """
    Searches for events using the Ticketmaster Discovery API.

    :param api_key: Your API key for accessing the Ticketmaster Discovery API.
    :param params: A dictionary of parameters to filter the search.
    :return: A list of events or an error message.
    """
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params['apikey'] = api_key

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors

        events_data = response.json()

        if '_embedded' in events_data and 'events' in events_data['_embedded']:
            events = events_data['_embedded']['events']
            return events
        else:
            return "No events found for the given parameters."
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"
    except Exception as err:
        return f"Other error occurred: {err}"


def search_venues(api_key, params):
    api_key = os.getenv('TICKET_MASTER_API_KEY')  # Retrieve API key from environment variable

    if not api_key:
        raise ValueError("Please set the TICKET_MASTER_API_KEY environment variable.")

    search_params = {
        'keyword': 'music',
        'city': 'Los Angeles',
        'stateCode': 'CA',
        'classificationName': 'Music',
        'size': '5'
    }
    events = search_events(api_key, search_params)
    if isinstance(events, list):
        for event in events:
            print(event['name'])
    else:
        print(events)