#!/usr/bin/env python3
"""
Enhanced script to fetch rugby player data from multiple teams
Includes better rate limiting and error handling
"""

import os
import time
import json
import requests
from dotenv import load_dotenv
from collections import Counter
from datetime import datetime

# Load environment variables
load_dotenv(override=True)

# Configuration
API_KEY = os.getenv('SPORTRADAR_API_KEY')
BASE_URL = "https://api.sportradar.com/rugby-union/trial/v3/en"
DELAY_BETWEEN_REQUESTS = 5  # seconds for trial API

def safe_api_call(url, params, delay=DELAY_BETWEEN_REQUESTS):
    """Make an API call with rate limit protection"""
    print(f"  Waiting {delay} seconds before API call...")
    time.sleep(delay)
    
    response = requests.get(url, params=params)
    
    if response.status_code == 429:
        print("  ⚠️  Rate limit hit! Waiting 10 seconds...")
        time.sleep(10)
        response = requests.get(url, params=params)
    
    return response

def get_competitions():
    """Get all available competitions"""
    url = f"{BASE_URL}/competitions.json"
    print("Fetching competitions...")
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp.status_code == 200:
        return resp.json().get('competitions', [])
    else:
        print(f"Error getting competitions: {resp.status_code}")
        return []

def get_competition_seasons(competition_id):
    """Get all seasons for a competition"""
    url = f"{BASE_URL}/competitions/{competition_id}/seasons.json"
    print("Fetching seasons...")
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp.status_code == 200:
        return resp.json().get('seasons', [])
    else:
        print(f"Error getting seasons: {resp.status_code}")
        return []

def get_season_competitors(season_id):
    """Get all competitors (teams) in a season"""
    url = f"{BASE_URL}/seasons/{season_id}/competitors.json"
    print("Fetching competitors...")
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
        print(f"  Error getting competitor profile: {resp.status_code}")
        return {}

def main():
    """Main function to fetch rugby player data from multiple teams"""
    
    if not API_KEY or API_KEY == 'your-sportradar-key-if-not-using-env':
        print("ERROR: Please set SPORTRADAR_API_KEY in your .env file")
        return
    
    print("=" * 70)
    print("🏉 Rugby Player Data Fetcher - Sportradar API")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Get competitions
    competitions = get_competitions()
    if not competitions:
        print("No competitions found!")
        return
    
    print(f"✅ Found {len(competitions)} competitions")
    
    # Find major competitions
    major_comps = {}
    for comp in competitions:
        name = comp.get('name', '')
        if 'Six Nations' in name and 'U20' not in name and 'Women' not in name:
            major_comps['six_nations'] = comp
        elif 'World Cup' in name and 'Women' not in name and 'Qualification' not in name:
            major_comps['world_cup'] = comp
        elif 'The Rugby Championship' in name:
            major_comps['rugby_championship'] = comp
    
    # Choose competition
    print("\nAvailable major competitions:")
    for key, comp in major_comps.items():
        print(f"  • {comp.get('name')} (ID: {comp.get('id')})")
    
    # Use Six Nations as default
    selected_comp = major_comps.get('six_nations')
    if not selected_comp:
        print("Six Nations not found, using first competition")
        selected_comp = competitions[0]
    
    print(f"\n📌 Selected: {selected_comp.get('name')}")
    
    # Step 2: Get seasons
    seasons = get_competition_seasons(selected_comp.get('id'))
    if not seasons:
        print("No seasons found!")
        return
    
    # Get the most recent season
    seasons_sorted = sorted(seasons, key=lambda x: x.get('year', ''), reverse=True)
    latest_season = seasons_sorted[0]
    
    print(f"✅ Using season: {latest_season.get('name')} ({latest_season.get('year')})")
    
    # Step 3: Get competitors
    competitors = get_season_competitors(latest_season.get('id'))
    if not competitors:
        print("No competitors found!")
        return
    
    print(f"✅ Found {len(competitors)} teams:\n")
    for i, comp in enumerate(competitors):
        print(f"  {i+1}. {comp.get('name')} ({comp.get('abbreviation', 'N/A')})")
    
    # Step 4: Get players from each competitor
    print(f"\n{'='*70}")
    print("Fetching player rosters (this will take a while due to rate limits)...")
    print(f"{'='*70}\n")
    
    all_teams_data = []
    total_players = 0
    
    for i, competitor in enumerate(competitors):
        comp_id = competitor.get('id')
        comp_name = competitor.get('name', 'Unknown')
        comp_abbr = competitor.get('abbreviation', 'N/A')
        
        print(f"\n[{i+1}/{len(competitors)}] {comp_name} ({comp_abbr})")
        print("-" * 40)
        
        if comp_id:
            profile = get_competitor_profile(comp_id)
            
            # Extract players
            players = profile.get('players', [])
            if not players and 'competitor' in profile:
                players = profile.get('competitor', {}).get('players', [])
            
            if players:
                print(f"  ✅ Found {len(players)} players")
                total_players += len(players)
                
                # Count positions
                positions = Counter()
                for player in players:
                    pos = player.get('type', player.get('position', 'Unknown'))
                    positions[pos] += 1
                
                # Save individual team file
                filename = f"{comp_name.replace(' ', '_').replace('/', '_').lower()}_roster.json"
                team_data = {
                    'team': comp_name,
                    'team_id': comp_id,
                    'abbreviation': comp_abbr,
                    'season': latest_season.get('name'),
                    'player_count': len(players),
                    'position_summary': dict(positions),
                    'players': players
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(team_data, f, indent=2, ensure_ascii=False)
                
                all_teams_data.append(team_data)
                print(f"  💾 Saved to {filename}")
                
                # Show position summary
                print(f"  📊 Positions: ", end="")
                for pos, count in positions.most_common():
                    print(f"{pos}:{count} ", end="")
                print()
                
            else:
                print("  ❌ No players found")
        
        # Be extra careful with rate limits
        if i < len(competitors) - 1:
            print(f"\n  ⏳ Waiting before next team...")
    
    # Save combined data
    if all_teams_data:
        summary_filename = f"{selected_comp.get('name', '').replace(' ', '_').lower()}_{latest_season.get('year')}_all_teams.json"
        summary_data = {
            'competition': selected_comp.get('name'),
            'season': latest_season.get('name'),
            'year': latest_season.get('year'),
            'teams_count': len(all_teams_data),
            'total_players': total_players,
            'generated_at': datetime.now().isoformat(),
            'teams': all_teams_data
        }
        
        with open(summary_filename, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*70}")
        print("✅ SUMMARY")
        print(f"{'='*70}")
        print(f"Competition: {selected_comp.get('name')}")
        print(f"Season: {latest_season.get('name')} ({latest_season.get('year')})")
        print(f"Teams processed: {len(all_teams_data)}")
        print(f"Total players: {total_players}")
        print(f"\n💾 All data saved to: {summary_filename}")
        print(f"💾 Individual team files also created")
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
if __name__ == "__main__":
    main() 