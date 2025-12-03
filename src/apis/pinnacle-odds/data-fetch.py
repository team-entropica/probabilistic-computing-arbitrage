import requests
import json
import time

headers = {
    "x-rapidapi-key": "3ca67aa802msh24fe1c798e3001ap1285dbjsndc55695dd39d",
    "x-rapidapi-host": "pinnacle-odds.p.rapidapi.com"
}

base_url = "https://pinnacle-odds.p.rapidapi.com"
s = requests.Session()
s.headers.update(headers)

all_sporting_events = {}

FOOTBALL_SPORT_ID = "1"

# In order: UCL, UCL corners, UCL bookings, La Liga, La Liga corners, La Liga bookings,
# Bundesliga, Bundesliga corners, Bundesliga bookings, Serie A, Serie A corners, Serie A bookings,
# Ligue 1, Ligue 1 corners, Ligue 1 bookings, BPL, BPL corners, BPL bookings,
MAIN_FOOTBALL_LEAGUES_IDS = "2627,5452,16325,2196,5490,32746,1842,5874,197439,2436,5488,197440,2036,6267,204807,1980,5487,197438"
# Only includes the leagues, no corners or bookings
MAIN_FOOTBALL_LEAGUE_IDS_SHORT = "2627,2196,1842,2436,2036,1980"

def get_sports():
    """Get all sports from Pinnacle Odds API."""
    response = s.get(base_url + '/kit/v1/sports')
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return json.loads(response.text)

# TODO: Add a since parameter to get markets that are still actively accessible
def get_markets(sport_id, prematch=True, leagues=None, has_odds=True):
    """
    Get markets from Pinnacle Odds API.
    sport_id: The ID of the sport to get markets for.
    prematch: Whether to get prematch markets.
    leagues: The IDs of the leagues to get markets for.
    has_odds: Whether to get markets with odds.
    Returns:
        A list of markets.
    """
    response = s.get(base_url + '/kit/v1/markets', params={'sport_id': sport_id, 'event_type': 'prematch', 'league_ids': leagues, 'is_have_odds': has_odds})
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    result = json.loads(response.text)
    for event in result['events']:
        all_sporting_events[event['event_id']] = event
        try:
            print('(%s)   %s: %s — %s %s' % (event["starts"], event['league_name'], event['home'], event['away'], event['periods']['num_0']['money_line']))
        except KeyError:
            pass
    return all_sporting_events


def get_football_leagues():
    """Get all football leagues from Pinnacle Odds API. Main leagues are already included at the top of the file."""
    response = s.get(base_url + '/kit/v1/leagues', params={'sport_id': "1"})
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return json.loads(response.text)




if __name__ == "__main__":
    get_markets(FOOTBALL_SPORT_ID, prematch=True, leagues=MAIN_FOOTBALL_LEAGUE_IDS_SHORT, has_odds=True)
