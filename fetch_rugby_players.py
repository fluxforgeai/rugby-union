#!/usr/bin/env python3
"""
Fetch Rugby Player Data from Sportradar API
This script demonstrates how to get player rosters from rugby teams
"""

import os
import time
import json
import requests
from dotenv import load_dotenv
from collections import Counter

# Load environment variables
load_dotenv(override=True)

# Configuration
API_KEY = os.getenv('SPORTRADAR_API_KEY')
BASE_URL = "https://api.sportradar.com/rugby-union/trial/v3/en"
DELAY_BETWEEN_REQUESTS = 5  # seconds

def safe_api_call(url, params, delay=DELAY_BETWEEN_REQUESTS):
    """Make an API call with rate limit protection"""
    print(f"Waiting {delay} seconds before API call...")
    time.sleep(delay)
    
    response = requests.get(url, params=params)
    
    if response.status_code == 429:
        print("Rate limit hit! Waiting 10 seconds...")
        time.sleep(10)
        response = requests.get(url, params=params)
    
    return response

def get_competitions():
    """Get all available competitions"""
    url = f"{BASE_URL}/competitions.json"
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp.status_code == 200:
        return resp.json().get('competitions', [])
    else:
        print(f"Error getting competitions: {resp.status_code}")
        return []

def get_competition_seasons(competition_id):
    """Get all seasons for a competition"""
    url = f"{BASE_URL}/competitions/{competition_id}/seasons.json"
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp.status_code == 200:
        return resp.json().get('seasons', [])
    else:
        print(f"Error getting seasons: {resp.status_code}")
        return []

def get_season_competitors(season_id):
    """Get all competitors (teams) in a season"""
    url = f"{BASE_URL}/seasons/{season_id}/competitors.json"
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp.status_code == 200:
        data = resp.json()
        return data.get('season_competitors', [])
    else:
        print(f"Error getting competitors: {resp.status_code}")
        return []

def get_competitor_profile(competitor_id):
    """Get competitor profile including players"""
    url = f"{BASE_URL}/competitors/{competitor_id}/profile.json"
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Error getting competitor profile: {resp.status_code}")
        return {}

def main():
    """Main function to fetch rugby player data"""
    
    if not API_KEY or API_KEY == 'your-sportradar-key-if-not-using-env':
        print("ERROR: Please set SPORTRADAR_API_KEY in your .env file")
        return
    
    print("Fetching Rugby Player Data from Sportradar API")
    print("=" * 60)
    
    # Step 1: Get competitions
    print("\nStep 1: Getting competitions...")
    competitions = get_competitions()
    
    if not competitions:
        print("No competitions found!")
        return
    
    print(f"Found {len(competitions)} competitions")
    
    # Find Six Nations (more likely to have current data)
    six_nations = None
    for comp in competitions:
        if 'Six Nations' in comp.get('name', ''):
            six_nations = comp
            break
    
    if not six_nations:
        print("Six Nations not found, using first competition")
        six_nations = competitions[0]
    
    print(f"\nUsing competition: {six_nations.get('name')}")
    print(f"Competition ID: {six_nations.get('id')}")
    
    # Step 2: Get seasons
    print("\nStep 2: Getting seasons...")
    seasons = get_competition_seasons(six_nations.get('id'))
    
    if not seasons:
        print("No seasons found!")
        return
    
    # Get the most recent season
    seasons_sorted = sorted(seasons, key=lambda x: x.get('year', ''), reverse=True)
    latest_season = seasons_sorted[0]
    
    print(f"Using season: {latest_season.get('name')} ({latest_season.get('year')})")
    print(f"Season ID: {latest_season.get('id')}")
    
    # Step 3: Get competitors
    print("\nStep 3: Getting competitors...")
    competitors = get_season_competitors(latest_season.get('id'))
    
    if not competitors:
        print("No competitors found!")
        return
    
    print(f"Found {len(competitors)} competitors")
    
    # Step 4: Get players from first competitor (to avoid rate limits)
    print("\nStep 4: Getting players from first competitor...")
    
    # The competitor data is directly in the list, not nested
    first_competitor = competitors[0]
    comp_id = first_competitor.get('id')
    comp_name = first_competitor.get('name', 'Unknown')
    comp_country = first_competitor.get('country', first_competitor.get('abbreviation', 'Unknown'))
    
    print(f"\nTeam: {comp_name}")
    print(f"Country: {comp_country}")
    print(f"ID: {comp_id}")
    
    if comp_id:
        print("\nFetching player roster...")
        profile = get_competitor_profile(comp_id)
        
        # Extract players
        players = profile.get('players', [])
        if not players and 'competitor' in profile:
            players = profile.get('competitor', {}).get('players', [])
        
        if players:
            print(f"\nFound {len(players)} players!")
            
            # Group by position
            positions = Counter()
            for player in players:
                pos = player.get('type', player.get('position', 'Unknown'))
                positions[pos] += 1
            
            print("\nPlayers by position:")
            for position, count in positions.most_common():
                print(f"- {position}: {count}")
            
            # Show first few players
            print("\nSample players:")
            for i, player in enumerate(players[:5]):
                name = player.get('name', 'Unknown')
                pos = player.get('type', 'Unknown')
                jersey = player.get('jersey_number', 'N/A')
                print(f"{i+1}. {name} - {pos} - Jersey #{jersey}")
            
            # Save to file
            filename = f"{comp_name.replace(' ', '_').replace('/', '_').lower()}_roster.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'team': comp_name,
                    'team_id': comp_id,
                    'country': comp_country,
                    'season': latest_season.get('name'),
                    'player_count': len(players),
                    'players': players
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Saved {len(players)} players to {filename}")
            
            print("\n" + "=" * 60)
            print("To get more teams, modify the script to loop through competitors")
            print("Remember to respect rate limits (5-10 seconds between requests)")
            
        else:
            print("No players found in the response")
    
if __name__ == "__main__":
    main() 