"""
Gradio web interface for Rugby Union Player Data Fetcher.

Provides a user-friendly web interface for fetching, filtering, and viewing
rugby player data using the Sportradar API.
"""

import gradio as gr
import pandas as pd
import json
import threading
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

from ..api.endpoints import RugbyEndpoints
from ..models.team import Team
from ..models.player import Player
from ..models.checkpoint import FetchCheckpoint
from ..utils.player_extractor import PlayerExtractor
from ..utils.data_saver import DataSaver
from ..config import Config


class ProgressTracker:
    """Tracks progress of data fetching operations for UI updates."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self.current_message = ""
        self.log_messages = []
        self.is_running = False
    
    def update(self, message: str) -> None:
        """
        Update progress with a new message.
        
        Args:
            message: Progress message to display
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"{timestamp} - {message}"
        
        self.current_message = formatted_message
        self.log_messages.append(formatted_message)
        
        # Keep only last 50 messages to prevent memory issues
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]
    
    def get_log(self) -> str:
        """Get formatted log of all messages."""
        return "\n".join(self.log_messages)
    
    def clear(self) -> None:
        """Clear all progress messages."""
        self.current_message = ""
        self.log_messages = []
        self.is_running = False


class RugbyDataInterface:
    """
    Main Gradio interface for the Rugby Union Player Data Fetcher.
    
    Provides two main tabs:
    1. Fetch Data: Select competitions/seasons and fetch player data
    2. View Data: Load and explore previously saved data
    """
    
    def __init__(self, endpoints: RugbyEndpoints):
        """
        Initialize the Gradio interface.
        
        Args:
            endpoints: RugbyEndpoints instance for API access
        """
        self.endpoints = endpoints
        self.player_extractor = PlayerExtractor(endpoints)
        self.data_saver = DataSaver()
        self.progress_tracker = ProgressTracker()
        
        # Set up progress callback for API client
        self.endpoints.client.update_progress = self.progress_tracker.update
        
        # Create the interface
        self.interface = self._create_interface()
    
    def _create_interface(self) -> gr.Blocks:
        """
        Create the Gradio interface with all components.
        
        Returns:
            gr.Blocks: Complete Gradio interface
        """
        with gr.Blocks(
            title="Rugby Union Player Data Fetcher",
            theme=gr.themes.Soft(),
        ) as interface:
            
            gr.Markdown("""
            # 🏉 Rugby Union Player Data Fetcher
            
            Fetch and analyze rugby player data from the Sportradar API with smart filtering capabilities.
            """)
            
            with gr.Tabs():
                # Tab 1: Fetch Data
                with gr.TabItem("Fetch Data"):
                    self._create_fetch_tab()
                
                # Tab 2: View Data  
                with gr.TabItem("View Data"):
                    self._create_view_tab()
        
        return interface
    
    def _create_fetch_tab(self) -> None:
        """Create the data fetching tab with all controls."""
        gr.Markdown("### Select Competition and Season")
        
        with gr.Row():
            with gr.Column():
                competition_dropdown = gr.Dropdown(
                    label="Competition",
                    choices=[("Select a competition", "none")],
                    value="none",
                    interactive=True
                )
                
                season_dropdown = gr.Dropdown(
                    label="Season", 
                    choices=[("Select a competition first", "none")],
                    value="none",
                    interactive=True
                )
            
            with gr.Column():
                filter_checkbox = gr.Checkbox(
                    label="Filter by actual participation",
                    value=True,
                    info="Show only players who actually played in matches (vs full team rosters)"
                )
                
                fetch_button = gr.Button(
                    "🏉 Fetch Player Data",
                    variant="primary",
                    size="lg"
                )
        
        # Progress display
        gr.Markdown("### Progress")
        progress_text = gr.Textbox(
            label="Current Status",
            interactive=False,
            lines=1
        )
        
        progress_log = gr.Textbox(
            label="Detailed Log", 
            interactive=False,
            lines=10,
            max_lines=15
        )
        
        # Results display
        gr.Markdown("### Results")
        
        with gr.Row():
            with gr.Column():
                results_table = gr.Dataframe(
                    label="Team Summary (Click team name to view players)",
                    interactive=False,
                    wrap=True
                )
            
            with gr.Column():
                download_file = gr.File(
                    label="Download Results",
                    interactive=False
                )
        
        # Set up event handlers
        self._setup_fetch_tab_events(
            competition_dropdown,
            season_dropdown, 
            filter_checkbox,
            fetch_button,
            progress_text,
            progress_log,
            results_table,
            download_file
        )
    
    def _create_view_tab(self) -> None:
        """Create the data viewing tab."""
        gr.Markdown("### Load Previously Saved Data")
        
        with gr.Row():
            load_latest_button = gr.Button(
                "📂 Load Latest Data",
                variant="secondary"
            )
            
            file_upload = gr.File(
                label="Or upload a data file",
                file_types=[".json"],
                file_count="single"
            )
        
        # Data display
        with gr.Row():
            team_selector = gr.Dropdown(
                label="Select Team to View Players",
                choices=[],
                interactive=True
            )
        
        # Team summary table
        team_summary_table = gr.Dataframe(
            label="Team Summary (Click team name to view players)",
            interactive=False
        )
        
        # Player details table
        player_details_table = gr.Dataframe(
            label="Player Details",
            interactive=False,
            wrap=True
        )
        
        # Data info
        data_info = gr.Textbox(
            label="Data Info",
            interactive=False,
            lines=3
        )
        
        # Set up event handlers
        self._setup_view_tab_events(
            load_latest_button,
            file_upload,
            team_selector,
            team_summary_table,
            player_details_table,
            data_info
        )
    
    def _setup_fetch_tab_events(self, competition_dropdown, season_dropdown, 
                               filter_checkbox, fetch_button, progress_text,
                               progress_log, results_table, download_file) -> None:
        """Set up event handlers for the fetch tab."""
        
        # Load competitions on startup
        competition_dropdown.choices = self._fetch_competitions()
        
        # Update seasons when competition changes
        competition_dropdown.change(
            fn=self._fetch_seasons,
            inputs=[competition_dropdown],
            outputs=[season_dropdown]
        )
        
        # Main fetch button
        fetch_button.click(
            fn=self._fetch_data_wrapper,
            inputs=[competition_dropdown, season_dropdown, filter_checkbox],
            outputs=[progress_text, progress_log, results_table, download_file]
        )
        
        # Auto-refresh progress every 2 seconds while fetching
        interface_state = gr.State({"refreshing": False})
        
        def refresh_progress(state):
            """Refresh progress display if fetching is active."""
            if self.progress_tracker.is_running:
                return {
                    "refreshing": True,
                    "progress": self.progress_tracker.current_message,
                    "log": self.progress_tracker.get_log()
                }
            return {"refreshing": False, "progress": "", "log": ""}
        
        # Set up periodic refresh (Note: This is a simplified approach)
        # In a real implementation, you'd use Gradio's event system more efficiently
    
    def _setup_view_tab_events(self, load_latest_button, file_upload, team_selector,
                              team_summary_table, player_details_table, data_info) -> None:
        """Set up event handlers for the view tab."""
        
        # Load latest data
        load_latest_button.click(
            fn=self._load_latest_data,
            outputs=[team_summary_table, team_selector, data_info]
        )
        
        # Upload file
        file_upload.change(
            fn=self._load_uploaded_data,
            inputs=[file_upload],
            outputs=[team_summary_table, team_selector, data_info]
        )
        
        # Team selection
        team_selector.change(
            fn=self._show_team_players,
            inputs=[team_selector],
            outputs=[player_details_table]
        )
    
    def _fetch_competitions(self) -> List[Tuple[str, str]]:
        """
        Fetch available competitions from API.
        
        Returns:
            List[Tuple[str, str]]: Competition choices for dropdown
        """
        if not Config.validate_api_key():
            return [("No API key configured", "no-key")]
        
        try:
            competitions = self.endpoints.get_competitions()
            if not competitions:
                return [("No competitions found", "none")]
            
            choices = []
            for comp in competitions:
                name = comp.get('name', 'Unknown')
                comp_id = comp.get('id', '')
                choices.append((name, comp_id))
            
            return sorted(choices)
            
        except Exception as e:
            return [(f"Error loading competitions: {str(e)}", "error")]
    
    def _fetch_seasons(self, competition_id: str) -> gr.Dropdown:
        """
        Fetch seasons for selected competition.
        
        Args:
            competition_id: Selected competition ID
            
        Returns:
            gr.Dropdown: Updated season dropdown
        """
        if not competition_id or competition_id in ["none", "no-key", "error"]:
            return gr.Dropdown(choices=[("Select a competition first", "none")])
        
        try:
            seasons = self.endpoints.get_competition_seasons(competition_id)
            if not seasons:
                return gr.Dropdown(choices=[("No seasons found", "none")])
            
            # Sort by year (most recent first)
            seasons_sorted = sorted(seasons, key=lambda x: x.get('year', ''), reverse=True)
            
            choices = []
            for season in seasons_sorted:
                name = f"{season.get('name', 'Unknown')} ({season.get('year', 'N/A')})"
                season_id = season.get('id', '')
                choices.append((name, season_id))
            
            return gr.Dropdown(choices=choices)
            
        except Exception as e:
            return gr.Dropdown(choices=[(f"Error loading seasons: {str(e)}", "error")])
    
    def _fetch_data_wrapper(self, competition_id: str, season_id: str, 
                           filter_participation: bool) -> Tuple[str, str, pd.DataFrame, str]:
        """
        Wrapper for data fetching that handles threading and UI updates.
        
        Args:
            competition_id: Selected competition ID
            season_id: Selected season ID  
            filter_participation: Whether to filter by participation
            
        Returns:
            Tuple: (progress_text, progress_log, results_table, download_file)
        """
        # Validate inputs
        if not Config.validate_api_key():
            error_msg = "ERROR: Please set SPORTRADAR_API_KEY in your .env file"
            return error_msg, error_msg, pd.DataFrame(), None
        
        if not competition_id or competition_id == "none" or not season_id or season_id == "none":
            error_msg = "ERROR: Please select both competition and season"
            return error_msg, error_msg, pd.DataFrame(), None
        
        # Clear previous progress
        self.progress_tracker.clear()
        self.progress_tracker.is_running = True
        
        # Start fetching in background thread
        def fetch_thread():
            try:
                self._fetch_rugby_data(competition_id, season_id, filter_participation)
            finally:
                self.progress_tracker.is_running = False
        
        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()
        
        # Return initial state
        return "Starting data fetch...", "Starting...", pd.DataFrame(), None
    
    def _fetch_rugby_data(self, competition_id: str, season_id: str, 
                         filter_participation: bool) -> None:
        """
        Fetch rugby data for the specified competition and season.
        
        Args:
            competition_id: Sportradar competition identifier
            season_id: Sportradar season identifier
            filter_participation: Whether to filter by actual participation
        """
        try:
            # Try to load existing checkpoint
            checkpoint = FetchCheckpoint.load(competition_id, season_id)
            if checkpoint and checkpoint.filter_participation == filter_participation:
                self.progress_tracker.update("Resuming from checkpoint...")
                teams_data = [Team.from_api_data(
                    {"id": team_data["team_id"], "name": team_data["team"], 
                     "abbreviation": team_data["abbreviation"]},
                    team_data["players"],
                    team_data["filtered_by_participation"]
                ) for team_data in checkpoint.all_teams_data]
            else:
                # Start fresh
                self.progress_tracker.update("Starting fresh data fetch...")
                checkpoint = FetchCheckpoint(competition_id, season_id, filter_participation)
                teams_data = []
            
            # Get competitors
            competitors = self.endpoints.get_season_competitors(season_id)
            if not competitors:
                self.progress_tracker.update("ERROR: No competitors found!")
                return
            
            self.progress_tracker.update(f"Found {len(competitors)} teams")
            
            # Process each team
            for i, competitor_item in enumerate(competitors):
                # Handle different API structures
                if 'competitor' in competitor_item:
                    competitor = competitor_item['competitor']
                else:
                    competitor = competitor_item
                
                comp_id = competitor.get('id')
                comp_name = competitor.get('name', 'Unknown')
                comp_abbr = competitor.get('abbreviation', 'N/A')
                
                # Skip if already processed
                if comp_id in checkpoint.completed_teams:
                    self.progress_tracker.update(f"[{i+1}/{len(competitors)}] Skipping {comp_name} (already processed)")
                    continue
                
                self.progress_tracker.update(f"[{i+1}/{len(competitors)}] Processing {comp_name} ({comp_abbr})...")
                
                if comp_id:
                    try:
                        if filter_participation:
                            # Build player list from match data
                            self.progress_tracker.update(f"Building player list from matches for {comp_name}...")
                            players = self.player_extractor.extract_players_from_season(season_id, comp_id)
                            
                            if not players:
                                # Fall back to full roster
                                self.progress_tracker.update(f"No match data found for {comp_name}, fetching full roster...")
                                profile = self.endpoints.get_competitor_profile(comp_id)
                                players_data = profile.get('players', [])
                                if not players_data and 'competitor' in profile:
                                    players_data = profile.get('competitor', {}).get('players', [])
                                players = [Player.from_api_data(p) for p in players_data]
                        else:
                            # Get full roster
                            profile = self.endpoints.get_competitor_profile(comp_id)
                            players_data = profile.get('players', [])
                            if not players_data and 'competitor' in profile:
                                players_data = profile.get('competitor', {}).get('players', [])
                            players = [Player.from_api_data(p) for p in players_data]
                        
                        # Create team object
                        team = Team(
                            id=comp_id,
                            name=comp_name,
                            abbreviation=comp_abbr,
                            players=players,
                            filtered_by_participation=filter_participation
                        )
                        
                        if players:
                            self.progress_tracker.update(f"Found {len(players)} players for {comp_name}")
                        else:
                            self.progress_tracker.update(f"No players found for {comp_name}")
                            team.error_message = "Could not fetch player data"
                        
                        teams_data.append(team)
                        
                        # Update checkpoint
                        checkpoint.all_teams_data.append(team.to_dict())
                        checkpoint.total_players += len(players)
                        checkpoint.completed_teams.add(comp_id)
                        checkpoint.save()
                        
                    except Exception as e:
                        self.progress_tracker.update(f"Error processing {comp_name}: {str(e)}")
                        # Still mark as completed to avoid infinite retries
                        checkpoint.completed_teams.add(comp_id)
                        checkpoint.save()
            
            # Save final results
            if teams_data:
                filepath = self.data_saver.save_teams_data(
                    teams_data, competition_id, season_id, filter_participation
                )
                self.progress_tracker.update(f"✅ Data saved to: {filepath}")
                
                # Clean up checkpoint
                checkpoint.cleanup()
                
                total_players = sum(team.player_count for team in teams_data)
                self.progress_tracker.update(f"🎉 Completed! {len(teams_data)} teams, {total_players} total players")
            else:
                self.progress_tracker.update("❌ No data collected")
                
        except Exception as e:
            self.progress_tracker.update(f"❌ Fatal error: {str(e)}")
    
    def _load_latest_data(self) -> Tuple[pd.DataFrame, gr.Dropdown, str]:
        """
        Load the most recent data file.
        
        Returns:
            Tuple: (team_summary, team_selector, data_info)
        """
        try:
            filepath = self.data_saver.get_latest_data_file()
            return self._load_data_file(filepath)
        except FileNotFoundError:
            empty_df = pd.DataFrame({"Message": ["No data files found"]})
            return empty_df, gr.Dropdown(choices=[]), "No data files found"
        except Exception as e:
            error_df = pd.DataFrame({"Error": [str(e)]})
            return error_df, gr.Dropdown(choices=[]), f"Error loading data: {e}"
    
    def _load_uploaded_data(self, file_path: str) -> Tuple[pd.DataFrame, gr.Dropdown, str]:
        """
        Load data from uploaded file.
        
        Args:
            file_path: Path to uploaded file
            
        Returns:
            Tuple: (team_summary, team_selector, data_info)
        """
        if not file_path:
            return pd.DataFrame(), gr.Dropdown(choices=[]), ""
        
        return self._load_data_file(file_path)
    
    def _load_data_file(self, filepath: str) -> Tuple[pd.DataFrame, gr.Dropdown, str]:
        """
        Load data from a JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Tuple: (team_summary, team_selector, data_info)
        """
        try:
            data = self.data_saver.load_teams_data(filepath)
            
            # Create team summary
            teams_summary = []
            team_choices = []
            
            for team_data in data.get('teams', []):
                teams_summary.append({
                    'Team': team_data.get('team', 'Unknown'),
                    'Abbreviation': team_data.get('abbreviation', ''),
                    'Player Count': team_data.get('player_count', 0)
                })
                
                team_choices.append((
                    team_data.get('team', 'Unknown'),
                    team_data.get('team_id', '')
                ))
            
            summary_df = pd.DataFrame(teams_summary)
            
            # Create data info
            info_text = f"""Loaded: {filepath.split('/')[-1]} (Filtered to show only players who participated)
Competition: {data.get('competition_id', 'Unknown')}
Season: {data.get('season_id', 'Unknown')}
Total Teams: {data.get('total_teams', 0)}
Total Players: {data.get('total_players', 0)}
Generated: {data.get('generated_at', 'Unknown')}"""
            
            # Store data for team selection
            self._current_data = data
            
            return summary_df, gr.Dropdown(choices=team_choices), info_text
            
        except Exception as e:
            error_df = pd.DataFrame({"Error": [f"Failed to load file: {str(e)}"]})
            return error_df, gr.Dropdown(choices=[]), f"Error: {e}"
    
    def _show_team_players(self, team_id: str) -> pd.DataFrame:
        """
        Show players for selected team.
        
        Args:
            team_id: Selected team ID
            
        Returns:
            pd.DataFrame: Players data
        """
        if not hasattr(self, '_current_data') or not team_id:
            return pd.DataFrame()
        
        # Find team data
        for team_data in self._current_data.get('teams', []):
            if team_data.get('team_id') == team_id:
                players = team_data.get('players', [])
                
                if not players:
                    return pd.DataFrame({"Message": ["No players found for this team"]})
                
                # Convert to DataFrame
                players_df = []
                for player in players:
                    players_df.append({
                        'Name': player.get('name', 'Unknown'),
                        'Position': player.get('type', 'Unknown'),
                        'Jersey': player.get('jersey_number', ''),
                        'Date of Birth': player.get('date_of_birth', ''),
                        'Height (cm)': player.get('height', ''),
                        'Weight (kg)': player.get('weight', ''),
                        'Nationality': player.get('nationality', '')
                    })
                
                return pd.DataFrame(players_df)
        
        return pd.DataFrame({"Message": ["Team not found"]})
    
    def launch(self, **kwargs) -> None:
        """
        Launch the Gradio interface.
        
        Args:
            **kwargs: Arguments to pass to gr.Blocks.launch()
        """
        return self.interface.launch(**kwargs)