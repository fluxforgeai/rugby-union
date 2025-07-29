#!/usr/bin/env python3
"""
Gradio UI for fetching rugby player data from Sportradar API
"""

import os
import time
import json
import requests
import gradio as gr
import pandas as pd
from dotenv import load_dotenv
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
import threading
import socket
import argparse
import pickle
from pathlib import Path

# Load environment variables
load_dotenv(override=True)

# Configuration
API_KEY = os.getenv('SPORTRADAR_API_KEY')
BASE_URL = "https://api.sportradar.com/rugby-union/trial/v3/en"
DELAY_BETWEEN_REQUESTS = 5  # seconds for trial API

# Global variables for progress tracking
progress_info = {"current": "", "log": []}
fetch_thread = None
CHECKPOINT_DIR = Path("rugby_data_checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)

def safe_api_call(url: str, params: dict, delay: int = DELAY_BETWEEN_REQUESTS, max_retries: int = 3) -> Optional[requests.Response]:
    """Make an API call with rate limit protection and retry logic"""
    update_progress(f"Waiting {delay} seconds before API call...")
    time.sleep(delay)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                update_progress("⚠️ Rate limit hit! Waiting 10 seconds...")
                time.sleep(10)
                continue
            
            return response
            
        except requests.exceptions.ConnectionError as e:
            update_progress(f"❌ Connection error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                update_progress(f"⏳ Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                update_progress("❌ Max retries reached. Connection failed.")
                return None
                
        except requests.exceptions.Timeout:
            update_progress(f"⏱️ Request timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                return None
                
        except Exception as e:
            update_progress(f"❌ Unexpected error: {str(e)}")
            return None
    
    return None

def update_progress(message: str):
    """Update progress information"""
    progress_info["current"] = message
    progress_info["log"].append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")

class FetchCheckpoint:
    """Manages checkpoint data for resumable fetching"""
    def __init__(self, competition_id: str, season_id: str, filter_participation: bool):
        self.competition_id = competition_id
        self.season_id = season_id
        self.filter_participation = filter_participation
        self.completed_teams = set()
        self.all_teams_data = []
        self.total_players = 0
        self.checkpoint_file = CHECKPOINT_DIR / f"checkpoint_{competition_id}_{season_id}.pkl"
    
    def save(self):
        """Save checkpoint to disk"""
        with open(self.checkpoint_file, 'wb') as f:
            pickle.dump({
                'competition_id': self.competition_id,
                'season_id': self.season_id,
                'filter_participation': self.filter_participation,
                'completed_teams': self.completed_teams,
                'all_teams_data': self.all_teams_data,
                'total_players': self.total_players
            }, f)
        update_progress(f"💾 Checkpoint saved ({len(self.completed_teams)} teams completed)")
    
    @classmethod
    def load(cls, competition_id: str, season_id: str) -> Optional['FetchCheckpoint']:
        """Load checkpoint from disk if exists"""
        checkpoint_file = CHECKPOINT_DIR / f"checkpoint_{competition_id}_{season_id}.pkl"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'rb') as f:
                    data = pickle.load(f)
                
                checkpoint = cls(
                    data['competition_id'],
                    data['season_id'],
                    data['filter_participation']
                )
                checkpoint.completed_teams = data['completed_teams']
                checkpoint.all_teams_data = data['all_teams_data']
                checkpoint.total_players = data['total_players']
                
                update_progress(f"📂 Resumed from checkpoint ({len(checkpoint.completed_teams)} teams already completed)")
                return checkpoint
            except Exception as e:
                update_progress(f"⚠️ Could not load checkpoint: {str(e)}")
                return None
        return None
    
    def cleanup(self):
        """Remove checkpoint file after successful completion"""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            update_progress("🧹 Checkpoint cleaned up")

def get_competitions() -> List[Dict]:
    """Get all available competitions"""
    url = f"{BASE_URL}/competitions.json"
    update_progress("Fetching competitions...")
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp and resp.status_code == 200:
        return resp.json().get('competitions', [])
    else:
        update_progress(f"Error getting competitions: {resp.status_code if resp else 'Network error'}")
        return []

def get_competition_seasons(competition_id: str) -> List[Dict]:
    """Get all seasons for a competition"""
    url = f"{BASE_URL}/competitions/{competition_id}/seasons.json"
    update_progress("Fetching seasons...")
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp and resp.status_code == 200:
        return resp.json().get('seasons', [])
    else:
        update_progress(f"Error getting seasons: {resp.status_code if resp else 'Network error'}")
        return []

def get_season_competitors(season_id: str) -> List[Dict]:
    """Get all competitors (teams) in a season"""
    url = f"{BASE_URL}/seasons/{season_id}/competitors.json"
    update_progress("Fetching competitors...")
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp and resp.status_code == 200:
        data = resp.json()
        return data.get('season_competitors', [])
    else:
        update_progress(f"Error getting competitors: {resp.status_code if resp else 'Network error'}")
        return []

def get_season_summaries(season_id: str) -> Dict:
    """Get season summaries including matches"""
    url = f"{BASE_URL}/seasons/{season_id}/summaries.json"
    update_progress("Fetching season match summaries...")
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp and resp.status_code == 200:
        return resp.json()
    else:
        update_progress(f"Error getting season summaries: {resp.status_code if resp else 'Network error'}")
        return {}

def get_sport_event_summary(sport_event_id: str) -> Dict:
    """Get sport event summary including player statistics"""
    url = f"{BASE_URL}/sport_events/{sport_event_id}/summary.json"
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp and resp.status_code == 200:
        return resp.json()
    else:
        return {}

def get_sport_event_lineups(sport_event_id: str) -> Dict:
    """Get sport event lineups including player participation data"""
    url = f"{BASE_URL}/sport_events/{sport_event_id}/lineups.json"
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp and resp.status_code == 200:
        return resp.json()
    else:
        return {}

def extract_players_from_matches(season_id: str, competitor_id: str) -> Set[str]:
    """Extract player IDs who actually played in the season for a specific team"""
    player_ids = set()
    
    # Get season summaries which contain match statistics
    summaries = get_season_summaries(season_id)
    if not summaries:
        update_progress("Could not get season summaries")
        return player_ids
    
    # Get all match summaries
    summaries_list = summaries.get('summaries', [])
    update_progress(f"Found {len(summaries_list)} matches in season")
    
    # Check each match for our team's participation
    team_matches_found = 0
    matches_checked = 0
    max_matches_to_check = 10  # Limit to avoid hitting rate limits
    
    for summary in summaries_list:
        if matches_checked >= max_matches_to_check:
            break
            
        sport_event = summary.get('sport_event', {})
        competitors = sport_event.get('competitors', [])
        
        # Check if our team played in this match
        team_in_match = False
        for comp in competitors:
            if comp.get('id') == competitor_id:
                team_in_match = True
                break
        
        if team_in_match:
            team_matches_found += 1
            matches_checked += 1
            players_found_in_this_match = False
            
            # Try to get players from the summary statistics first
            match_stats = summary.get('statistics', {})
            if match_stats and 'totals' in match_stats:
                totals = match_stats['totals']
                competitors_stats = totals.get('competitors', [])
                
                for comp_stats in competitors_stats:
                    if comp_stats.get('id') == competitor_id:
                        # Found our team's statistics
                        players = comp_stats.get('players', [])
                        for player in players:
                            player_id = player.get('id')
                            if player_id:
                                player_ids.add(player_id)
                                players_found_in_this_match = True
                        update_progress(f"Found {len(players)} players in match {team_matches_found}")
                        break
            
            # If no players found in this match's summary, try the detailed sport event
            if not players_found_in_this_match:
                sport_event_id = sport_event.get('id')
                if sport_event_id:
                    update_progress(f"Checking detailed match data for match {team_matches_found}...")
                    detailed_match = get_sport_event_summary(sport_event_id)
                    
                    if detailed_match and 'statistics' in detailed_match:
                        detailed_stats = detailed_match['statistics']
                        if 'totals' in detailed_stats:
                            totals = detailed_stats['totals']
                            competitors_stats = totals.get('competitors', [])
                            
                            for comp_stats in competitors_stats:
                                if comp_stats.get('id') == competitor_id:
                                    players = comp_stats.get('players', [])
                                    for player in players:
                                        player_id = player.get('id')
                                        if player_id:
                                            player_ids.add(player_id)
                                    update_progress(f"Found {len(players)} players in detailed match {team_matches_found}")
                                    players_found_in_this_match = True
                                    break
                    
                    # If still no players found in statistics, try lineups endpoint
                    if not players_found_in_this_match:
                        update_progress(f"Checking lineups data for match {team_matches_found}...")
                        lineups_data = get_sport_event_lineups(sport_event_id)
                        
                        if lineups_data and 'lineups' in lineups_data:
                            lineups = lineups_data['lineups']
                            competitors_lineups = lineups.get('competitors', [])
                            
                            for comp_lineup in competitors_lineups:
                                if comp_lineup.get('id') == competitor_id:
                                    players = comp_lineup.get('players', [])
                                    players_who_played = 0
                                    for player in players:
                                        # Only include players who actually played
                                        if player.get('played') == True:
                                            player_id = player.get('id')
                                            if player_id:
                                                player_ids.add(player_id)
                                                players_who_played += 1
                                    update_progress(f"Found {players_who_played} players who played in match {team_matches_found} (from lineups)")
                                    break
    
    if team_matches_found > 0:
        update_progress(f"Checked {team_matches_found} matches, found {len(player_ids)} unique players who participated")
    else:
        update_progress(f"Team {competitor_id} not found in any matches")
    
    return player_ids

def get_competitor_profile(competitor_id: str) -> Dict:
    """Get competitor profile including players"""
    url = f"{BASE_URL}/competitors/{competitor_id}/profile.json"
    resp = safe_api_call(url, {"api_key": API_KEY})
    
    if resp and resp.status_code == 200:
        return resp.json()
    else:
        update_progress(f"Error getting competitor profile: {resp.status_code if resp else 'Network error'}")
        return {}

def fetch_all_competitions() -> List[Tuple[str, str]]:
    """Fetch all competitions and return as choices for dropdown"""
    if not API_KEY or API_KEY == 'your-sportradar-key-if-not-using-env':
        return [("No API Key", "no-key")]
    
    competitions = get_competitions()
    if not competitions:
        return [("No competitions found", "none")]
    
    # Filter and format competitions
    choices = []
    for comp in competitions:
        name = comp.get('name', 'Unknown')
        comp_id = comp.get('id', '')
        # Prioritize major competitions
        if any(term in name for term in ['Six Nations', 'World Cup', 'The Rugby Championship']) \
           and 'U20' not in name and 'Women' not in name:
            choices.insert(0, (name, comp_id))
        else:
            choices.append((name, comp_id))
    
    return choices if choices else [("No competitions found", "none")]

def fetch_seasons_for_competition(competition_id: str) -> List[Tuple[str, str]]:
    """Fetch seasons for selected competition"""
    if not competition_id or competition_id == "none" or competition_id == "no-key":
        return [("Select a competition first", "none")]
    
    seasons = get_competition_seasons(competition_id)
    if not seasons:
        return [("No seasons found", "none")]
    
    # Sort by year (most recent first)
    seasons_sorted = sorted(seasons, key=lambda x: x.get('year', ''), reverse=True)
    
    choices = []
    for season in seasons_sorted:
        name = f"{season.get('name', 'Unknown')} ({season.get('year', 'N/A')})"
        season_id = season.get('id', '')
        choices.append((name, season_id))
    
    return choices

def fetch_rugby_data_threaded(competition_id: str, season_id: str, filter_by_participation: bool = False):
    """Fetch rugby data in a separate thread with checkpoint support"""
    global progress_info
    progress_info = {"current": "", "log": []}
    
    if not API_KEY or API_KEY == 'your-sportradar-key-if-not-using-env':
        update_progress("ERROR: Please set SPORTRADAR_API_KEY in your .env file")
        return
    
    if not competition_id or competition_id == "none" or not season_id or season_id == "none":
        update_progress("ERROR: Please select both competition and season")
        return
    
    # Try to load checkpoint
    checkpoint = FetchCheckpoint.load(competition_id, season_id)
    if checkpoint and checkpoint.filter_participation == filter_by_participation:
        update_progress("Resuming from checkpoint...")
        all_teams_data = checkpoint.all_teams_data
        total_players = checkpoint.total_players
    else:
        update_progress("Starting fresh data fetch...")
        checkpoint = FetchCheckpoint(competition_id, season_id, filter_by_participation)
        all_teams_data = []
        total_players = 0
    
    # Get competitors
    competitors = get_season_competitors(season_id)
    if not competitors:
        update_progress("No competitors found!")
        return
    
    update_progress(f"Found {len(competitors)} teams")
    
    # Create output directory
    output_dir = "rugby_data_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each competitor
    for i, competitor_item in enumerate(competitors):
        # Handle different API structures - sometimes competitors are nested, sometimes direct
        if 'competitor' in competitor_item:
            competitor = competitor_item['competitor']
        else:
            competitor = competitor_item
            
        comp_id = competitor.get('id')
        comp_name = competitor.get('name', 'Unknown')
        comp_abbr = competitor.get('abbreviation', 'N/A')
        
        # Skip if already processed
        if comp_id in checkpoint.completed_teams:
            update_progress(f"[{i+1}/{len(competitors)}] Skipping {comp_name} (already processed)")
            continue
        
        update_progress(f"[{i+1}/{len(competitors)}] Fetching {comp_name} ({comp_abbr})...")
        
        if comp_id:
            profile = get_competitor_profile(comp_id)
            
            # Extract players
            players = profile.get('players', [])
            if not players and 'competitor' in profile:
                players = profile.get('competitor', {}).get('players', [])
            
            if players:
                update_progress(f"Found {len(players)} players for {comp_name}")
                
                # Filter by actual participation if requested
                if filter_by_participation:
                    update_progress(f"Filtering players who actually played for {comp_name}...")
                    participated_player_ids = extract_players_from_matches(season_id, comp_id)
                    
                    if participated_player_ids:
                        # Filter players to only those who participated
                        original_count = len(players)
                        players = [p for p in players if p.get('id') in participated_player_ids]
                        update_progress(f"Filtered from {original_count} to {len(players)} players who actually played")
                    else:
                        update_progress(f"Could not determine participated players, using full roster")
                
                total_players += len(players)
                
                # Count positions
                positions = Counter()
                for player in players:
                    pos = player.get('type', player.get('position', 'Unknown'))
                    positions[pos] += 1
                
                # Save team data
                team_data = {
                    'team': comp_name,
                    'team_id': comp_id,
                    'abbreviation': comp_abbr,
                    'player_count': len(players),
                    'position_summary': dict(positions),
                    'players': players,
                    'filtered_by_participation': filter_by_participation
                }
                
                all_teams_data.append(team_data)
                checkpoint.all_teams_data = all_teams_data
                checkpoint.total_players = total_players
                checkpoint.completed_teams.add(comp_id)
                checkpoint.save()
            else:
                update_progress(f"No players found for {comp_name}")
                # Still mark as completed to avoid retrying
                checkpoint.completed_teams.add(comp_id)
                checkpoint.save()
    
    # Save combined data
    if all_teams_data:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_filename = os.path.join(output_dir, f"rugby_data_{timestamp}.json")
        
        summary_data = {
            'competition_id': competition_id,
            'season_id': season_id,
            'teams_count': len(all_teams_data),
            'total_players': total_players,
            'generated_at': datetime.now().isoformat(),
            'filtered_by_participation': filter_by_participation,
            'teams': all_teams_data
        }
        
        with open(summary_filename, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        update_progress(f"✅ Complete! Saved {total_players} players from {len(all_teams_data)} teams to {summary_filename}")
        # Clean up checkpoint after successful completion
        checkpoint.cleanup()
    else:
        update_progress("❌ No data fetched")

def start_fetch(competition_id: str, season_id: str, filter_participation: bool) -> str:
    """Start fetching data in a background thread"""
    global fetch_thread
    
    if fetch_thread and fetch_thread.is_alive():
        return "A fetch operation is already in progress. Please wait."
    
    fetch_thread = threading.Thread(
        target=fetch_rugby_data_threaded,
        args=(competition_id, season_id, filter_participation)
    )
    fetch_thread.start()
    
    filter_msg = " (filtering by actual participation)" if filter_participation else ""
    return f"Fetch started{filter_msg}! Check the progress log below."

def get_progress() -> Tuple[str, str]:
    """Get current progress status"""
    current = progress_info.get("current", "No operation in progress")
    log = "\n".join(progress_info.get("log", []))
    return current, log

def check_checkpoint(competition_id: str, season_id: str) -> str:
    """Check if a checkpoint exists for the given competition and season"""
    if not competition_id or competition_id == "none" or not season_id or season_id == "none":
        return "No checkpoint found"
    
    checkpoint_file = CHECKPOINT_DIR / f"checkpoint_{competition_id}_{season_id}.pkl"
    if checkpoint_file.exists():
        try:
            with open(checkpoint_file, 'rb') as f:
                data = pickle.load(f)
            teams_done = len(data.get('completed_teams', set()))
            return f"✅ Checkpoint found: {teams_done} teams already completed. Will resume from there."
        except:
            return "⚠️ Checkpoint found but couldn't read it"
    return "No checkpoint found - will start fresh"

def load_saved_data() -> Tuple[pd.DataFrame, Dict]:
    """Load and display saved data"""
    output_dir = "rugby_data_output"
    
    if not os.path.exists(output_dir):
        return pd.DataFrame({"Message": ["No data found. Please fetch data first."]}), {}
    
    # Find the most recent file
    files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
    if not files:
        return pd.DataFrame({"Message": ["No data files found."]}), {}
    
    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
    filepath = os.path.join(output_dir, latest_file)
    
    # Load and parse data
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create summary dataframe without Positions column
    summary_data = []
    for team in data.get('teams', []):
        summary_data.append({
            'Team': team['team'],
            'Abbreviation': team['abbreviation'],
            'Player Count': team['player_count']
        })
    
    if summary_data:
        df = pd.DataFrame(summary_data)
        return df, data
    else:
        return pd.DataFrame({"Message": ["No team data found in file."]}), {}

def get_team_players(team_name: str, data: Dict) -> pd.DataFrame:
    """Get player details for a specific team"""
    if not data or not team_name:
        return pd.DataFrame({"Message": ["No team selected or data not loaded."]})
    
    # Find the team data
    for team in data.get('teams', []):
        if team['team'] == team_name:
            players = team.get('players', [])
            if not players:
                return pd.DataFrame({"Message": [f"No players found for {team_name}."]})
            
            # Create player dataframe
            player_data = []
            for player in players:
                player_data.append({
                    'Name': player.get('name', 'Unknown'),
                    'Position': player.get('type', 'Unknown'),
                    'Jersey #': player.get('jersey_number', '-'),
                    'Date of Birth': player.get('date_of_birth', 'Unknown'),
                    'Height (cm)': player.get('height', '-'),
                    'Weight (kg)': player.get('weight', '-'),
                    'Nationality': player.get('nationality', 'Unknown')
                })
            
            return pd.DataFrame(player_data)
    
    return pd.DataFrame({"Message": [f"Team {team_name} not found."]})

def create_ui():
    """Create and return the Gradio interface"""
    with gr.Blocks(title="Rugby Player Data Fetcher") as demo:
        gr.Markdown("# 🏉 Rugby Player Data Fetcher")
        gr.Markdown("Fetch player data from rugby teams using the Sportradar API")
        
        with gr.Tab("Fetch Data"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Configuration")
                    
                    # Competition dropdown
                    competition_dropdown = gr.Dropdown(
                        label="Select Competition",
                        choices=[("Loading competitions...", "loading")],
                        value="loading"
                    )
                    
                    # Season dropdown
                    season_dropdown = gr.Dropdown(
                        label="Select Season",
                        choices=[("Select a competition first", "none")],
                        value="none"
                    )
                    
                    # Filter checkbox
                    filter_checkbox = gr.Checkbox(
                        label="Only fetch players who actually played",
                        value=False,
                        info="This will take longer as it needs to check match data"
                    )
                    
                    # Checkpoint info
                    checkpoint_info = gr.Textbox(
                        label="Checkpoint Status",
                        value="No checkpoint found",
                        interactive=False
                    )
                    
                    # Fetch button
                    fetch_button = gr.Button("Start Fetching", variant="primary")
                    
                    # Status message
                    status_text = gr.Textbox(label="Status", value="Ready to fetch data")
                
                with gr.Column():
                    gr.Markdown("### Progress")
                    
                    # Current operation
                    current_op = gr.Textbox(
                        label="Current Operation",
                        value="No operation in progress",
                        interactive=False
                    )
                    
                    # Progress log
                    progress_log = gr.Textbox(
                        label="Progress Log",
                        value="",
                        lines=15,
                        interactive=False
                    )
                    
                    # Refresh button
                    refresh_button = gr.Button("Refresh Progress")
        
        with gr.Tab("View Data"):
            gr.Markdown("### Saved Data Summary")
            
            # Load data button
            load_button = gr.Button("Load Latest Data", variant="primary")
            
            # Store loaded data
            loaded_data = gr.State({})
            
            with gr.Row():
                with gr.Column(scale=1):
                    # Data display
                    data_display = gr.DataFrame(
                        label="Team Summary (Click team name to view players)",
                        interactive=False
                    )
                    
                    # File info
                    file_info = gr.Textbox(
                        label="Data Info",
                        value="Click 'Load Latest Data' to view saved data",
                        interactive=False
                    )
                
                with gr.Column(scale=2):
                    # Team selector
                    team_selector = gr.Dropdown(
                        label="Select Team to View Players",
                        choices=[],
                        value=None,
                        interactive=True
                    )
                    
                    # Player details display
                    player_display = gr.DataFrame(
                        label="Player Details",
                        interactive=False,
                        value=pd.DataFrame({"Message": ["Select a team to view players"]})
                    )
        
        # Event handlers
        def on_load():
            """Initialize competitions on load"""
            try:
                choices = fetch_all_competitions()
                return gr.update(choices=choices, value=choices[0][1] if choices else "none")
            except Exception as e:
                return gr.update(choices=[("Error loading competitions", "error")], value="error")
        
        def on_competition_change(competition_id):
            """Update seasons when competition changes"""
            try:
                choices = fetch_seasons_for_competition(competition_id)
                return gr.update(choices=choices, value=choices[0][1] if choices else "none"), "No checkpoint found"
            except Exception as e:
                return gr.update(choices=[("Error loading seasons", "error")], value="error"), "Error"
        
        def on_season_change(competition_id, season_id):
            """Check for checkpoint when season changes"""
            return check_checkpoint(competition_id, season_id)
        
        def on_load_data():
            """Load and display saved data"""
            try:
                df, data = load_saved_data()
                output_dir = "rugby_data_output"
                files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
                if files:
                    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
                    info = f"Loaded: {latest_file}"
                    if data.get('filtered_by_participation', False):
                        info += " (Filtered to show only players who participated)"
                else:
                    info = "No data files found"
                
                # Get team names for dropdown
                team_choices = []
                if data and 'teams' in data:
                    team_choices = [(team['team'], team['team']) for team in data['teams']]
                
                return df, info, data, gr.update(choices=team_choices, value=None)
            except Exception as e:
                return pd.DataFrame({"Error": [str(e)]}), f"Error: {str(e)}", {}, gr.update(choices=[], value=None)
        
        def on_team_select(team_name, data):
            """Display players for selected team"""
            if not team_name or not data:
                return pd.DataFrame({"Message": ["Select a team to view players"]})
            return get_team_players(team_name, data)
        
        # Wire up events
        demo.load(on_load, outputs=competition_dropdown)
        
        competition_dropdown.change(
            on_competition_change,
            inputs=competition_dropdown,
            outputs=[season_dropdown, checkpoint_info]
        )
        
        season_dropdown.change(
            on_season_change,
            inputs=[competition_dropdown, season_dropdown],
            outputs=checkpoint_info
        )
        
        fetch_button.click(
            start_fetch,
            inputs=[competition_dropdown, season_dropdown, filter_checkbox],
            outputs=status_text
        )
        
        refresh_button.click(
            get_progress,
            outputs=[current_op, progress_log]
        )
        
        load_button.click(
            on_load_data,
            outputs=[data_display, file_info, loaded_data, team_selector]
        )
        
        team_selector.change(
            on_team_select,
            inputs=[team_selector, loaded_data],
            outputs=player_display
        )
        
        # Timer for auto-refresh progress
        timer = gr.Timer(2.0)  # Update every 2 seconds
        timer.tick(
            get_progress,
            outputs=[current_op, progress_log]
        )
    
    return demo

def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is available for use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result != 0
    except Exception:
        return False

def find_available_port(start_port: int = 8000, end_port: int = 9000, host: str = "127.0.0.1") -> Optional[int]:
    """Find an available port in the given range"""
    print(f"Searching for available port between {start_port} and {end_port}...")
    
    for port in range(start_port, end_port + 1):
        if is_port_available(port, host):
            print(f"✅ Found available port: {port}")
            return port
    
    print(f"❌ No available ports found in range {start_port}-{end_port}")
    return None

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Rugby Player Data Fetcher - Gradio UI")
    parser.add_argument("--port", type=int, default=None, help="Specific port to use")
    parser.add_argument("--start-port", type=int, default=8000, help="Start of port range to search (default: 8000)")
    parser.add_argument("--end-port", type=int, default=9000, help="End of port range to search (default: 9000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Don't automatically open browser")
    parser.add_argument("--share", action="store_true", help="Create a public shareable link")
    
    args = parser.parse_args()
    
    # Check API key
    if not API_KEY or API_KEY == 'your-sportradar-key-if-not-using-env':
        print("⚠️  WARNING: SPORTRADAR_API_KEY not set in .env file")
        print("   The UI will launch but API calls will fail")
        print("")
    
    # Determine which port to use
    if args.port:
        # User specified a port
        if is_port_available(args.port, args.host):
            port = args.port
            print(f"✅ Using specified port: {port}")
        else:
            print(f"❌ Port {args.port} is not available")
            port = find_available_port(args.start_port, args.end_port, args.host)
            if not port:
                print("Failed to find an available port. Exiting.")
                exit(1)
    else:
        # Find an available port in the range
        port = find_available_port(args.start_port, args.end_port, args.host)
        if not port:
            print("Failed to find an available port. Exiting.")
            exit(1)
    
    # Create and launch the UI
    print(f"\n🏉 Starting Rugby Player Data Fetcher UI...")
    print(f"   Host: {args.host}")
    print(f"   Port: {port}")
    print(f"   Browser: {'Disabled' if args.no_browser else 'Will open automatically'}")
    print(f"   Share: {'Enabled' if args.share else 'Disabled'}")
    print("")
    
    demo = create_ui()
    
    try:
        demo.launch(
            share=args.share,
            server_name=args.host,
            server_port=port,
            inbrowser=not args.no_browser,
            quiet=False
        )
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Error launching server: {e}")