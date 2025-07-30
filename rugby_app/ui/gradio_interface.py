"""
Optimized Gradio web interface for Rugby Union Player Data Fetcher.

This version focuses on performance and eliminates initialization hangs by:
- Lazy loading of dropdowns
- Simplified event handlers
- Minimal state management
- Progressive enhancement approach
"""

import gradio as gr
import pandas as pd
import json
import threading
import os
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

from ..api.endpoints import RugbyEndpoints
from ..models.team import Team
from ..models.player import Player
from ..models.checkpoint import FetchCheckpoint
from ..utils.player_extractor import PlayerExtractor
from ..utils.data_saver import DataSaver
from ..config import Config


class OptimizedProgressTracker:
    """Lightweight progress tracker for UI updates."""
    
    def __init__(self):
        self.current_message = ""
        self.is_running = False
        self._log = []
    
    def update(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.current_message = f"{timestamp} - {message}"
        self._log.append(self.current_message)
        # Keep only last 30 messages for performance
        if len(self._log) > 30:
            self._log = self._log[-30:]
    
    def get_log(self) -> str:
        return "\n".join(self._log)
    
    def clear(self) -> None:
        self.current_message = ""
        self._log = []
        self.is_running = False


class RugbyDataInterface:
    """
    Optimized Gradio interface for the Rugby Union Player Data Fetcher.
    
    Key optimizations:
    - Lazy loading of data
    - Simplified component creation
    - Minimal event handlers
    - Progressive enhancement
    """
    
    def __init__(self, endpoints: RugbyEndpoints):
        """Initialize the optimized interface."""
        self.endpoints = endpoints
        self.player_extractor = PlayerExtractor(endpoints)
        self.data_saver = DataSaver()
        self.progress_tracker = OptimizedProgressTracker()
        
        # Set up progress callback
        self.endpoints.client.update_progress = self.progress_tracker.update
        
        # Cached data for performance
        self._competitions_cache = None
        self._current_data = None
        
        # Create the interface
        self.interface = self._create_interface()
    
    def _create_interface(self) -> gr.Blocks:
        """Create the optimized Gradio interface."""
        
        with gr.Blocks(
            title="Rugby Union Player Data Fetcher",
            theme=gr.themes.Soft(),
        ) as interface:
            
            gr.Markdown("""
            # 🏉 Rugby Union Player Data Fetcher
            Fetch and analyze rugby player data from the Sportradar API
            """)
            
            with gr.Tabs():
                # Fetch Data Tab
                with gr.TabItem("📥 Fetch Data"):
                    self._create_fetch_tab()
                
                # View Data Tab
                with gr.TabItem("📊 View Data"):
                    self._create_view_tab()
            
            # Real-time progress updates
            def update_progress():
                if hasattr(self, '_progress_components') and self.progress_tracker.is_running:
                    return (
                        self.progress_tracker.current_message, 
                        self.progress_tracker.get_log(),
                        self.get_current_results()
                    )
                elif not self.progress_tracker.is_running and hasattr(self, '_current_results'):
                    # Fetch completed, show final results
                    return (
                        "✅ Fetch completed - results available below",
                        self.progress_tracker.get_log(),
                        self.get_current_results()
                    )
                return gr.update(), gr.update(), gr.update()
            
            # Note: Real-time updates removed due to Gradio compatibility
            # Progress will update when user clicks fetch button
        
        return interface
    
    def _create_fetch_tab(self):
        """Create the optimized fetch tab."""
        
        gr.Markdown("### Select Competition and Season")
        
        with gr.Row():
            competition_dropdown = gr.Dropdown(
                label="Competition",
                choices=[("Click 'Load Competitions' to start", "none")],
                value="none",
                interactive=True
            )
            
            load_competitions_btn = gr.Button("🔄 Load Competitions", size="sm")
        
        with gr.Row():
            season_dropdown = gr.Dropdown(
                label="Season",
                choices=[("Select competition first", "none")],
                value="none",
                interactive=True
            )
            
            filter_checkbox = gr.Checkbox(
                label="Filter by actual participation",
                value=True,
                info="Show only players who actually played"
            )
        
        fetch_button = gr.Button("🏉 Fetch Player Data", variant="primary", size="lg")
        
        # Progress section
        gr.Markdown("### Progress")
        
        with gr.Row():
            progress_text = gr.Textbox(label="Status", interactive=False, lines=1, scale=4)
            refresh_btn = gr.Button("🔄 Refresh", size="sm", scale=1)
        
        progress_log = gr.Textbox(label="Log", interactive=False, lines=8)
        
        # Results section
        gr.Markdown("### Results")
        
        # Initialize results table with proper headers
        empty_results_df = pd.DataFrame({
            "Team": ["No data fetched yet"],
            "Abbreviation": [""],
            "Player Count": [""],
            "Status": ["Click 'Fetch Player Data' to start"]
        })
        
        results_table = gr.Dataframe(
            label="Team Summary", 
            interactive=False,
            value=empty_results_df
        )
        download_file = gr.File(label="Download Results", interactive=False)
        
        # Set up event handlers (simplified)
        self._setup_fetch_events(
            load_competitions_btn, competition_dropdown, season_dropdown,
            filter_checkbox, fetch_button, refresh_btn, progress_text, progress_log,
            results_table, download_file
        )
    
    def _create_view_tab(self):
        """Create the optimized view tab."""
        
        gr.Markdown("### Load Previously Saved Data")
        
        with gr.Row():
            load_latest_btn = gr.Button("📂 Load Latest Data", variant="secondary")
            file_upload = gr.File(label="Upload JSON file", file_types=[".json"])
        
        # Data display
        team_selector = gr.Dropdown(label="Select Team", choices=[], interactive=True)
        team_summary = gr.Dataframe(label="Team Summary", interactive=False)
        player_details = gr.Dataframe(label="Player Details", interactive=False)
        data_info = gr.Textbox(label="Data Info", interactive=False, lines=3)
        
        # Set up view events (simplified)
        self._setup_view_events(
            load_latest_btn, file_upload, team_selector,
            team_summary, player_details, data_info
        )
    
    def _setup_fetch_events(self, load_competitions_btn, competition_dropdown, 
                           season_dropdown, filter_checkbox, fetch_button, refresh_btn,
                           progress_text, progress_log, results_table, download_file):
        """Set up fetch tab events with optimization."""
        
        # Load competitions (lazy loading)
        def load_competitions():
            try:
                if not self._competitions_cache:
                    competitions = self.endpoints.get_competitions()
                    if competitions:
                        choices = [(comp.get('name', 'Unknown'), comp.get('id', '')) 
                                 for comp in competitions]
                        self._competitions_cache = sorted(choices)
                    else:
                        self._competitions_cache = [("No competitions found", "none")]
                
                return gr.Dropdown(choices=self._competitions_cache)
            except Exception as e:
                return gr.Dropdown(choices=[(f"Error: {str(e)}", "error")])
        
        load_competitions_btn.click(
            fn=load_competitions,
            outputs=[competition_dropdown]
        )
        
        # Load seasons when competition changes
        def load_seasons(competition_id):
            if not competition_id or competition_id in ["none", "error"]:
                return gr.Dropdown(choices=[("Select competition first", "none")])
            
            try:
                seasons = self.endpoints.get_competition_seasons(competition_id)
                if seasons:
                    # Sort by year (most recent first)
                    seasons_sorted = sorted(seasons, key=lambda x: x.get('year', ''), reverse=True)
                    choices = [(f"{s.get('name', 'Unknown')} ({s.get('year', 'N/A')})", 
                              s.get('id', '')) for s in seasons_sorted]
                    return gr.Dropdown(choices=choices)
                else:
                    return gr.Dropdown(choices=[("No seasons found", "none")])
            except Exception as e:
                return gr.Dropdown(choices=[(f"Error: {str(e)}", "error")])
        
        competition_dropdown.change(
            fn=load_seasons,
            inputs=[competition_dropdown],
            outputs=[season_dropdown]
        )
        
        # Fetch data (simplified)
        def start_fetch(competition_id, season_id, filter_participation):
            if not Config.validate_api_key():
                return "❌ API key not configured", "Error: Please set SPORTRADAR_API_KEY environment variable", pd.DataFrame({"Status": ["API key required"]}), None
            
            if not competition_id or competition_id == "none" or not season_id or season_id == "none":
                return "❌ Select competition and season", "Error: Both competition and season must be selected", pd.DataFrame({"Status": ["Selection required"]}), None
            
            # Get competition and season names for better logging
            comp_name = next((choice[0] for choice in self._competitions_cache if choice[1] == competition_id), competition_id)
            
            # Start background fetch
            self.progress_tracker.clear()
            self.progress_tracker.is_running = True
            self.progress_tracker.update(f"🏉 Starting fetch for {comp_name}")
            self.progress_tracker.update(f"📊 Filter by participation: {'Yes' if filter_participation else 'No'}")
            
            thread = threading.Thread(
                target=self._fetch_data_background,
                args=(competition_id, season_id, filter_participation),
                daemon=True
            )
            thread.start()
            
            initial_df = pd.DataFrame({"Status": ["Initializing fetch..."]})
            return f"🚀 Fetching {comp_name} data...", self.progress_tracker.get_log(), initial_df, None
        
        fetch_button.click(
            fn=start_fetch,
            inputs=[competition_dropdown, season_dropdown, filter_checkbox],
            outputs=[progress_text, progress_log, results_table, download_file]
        )
        
        # Store components for progress updates
        self._progress_components = (progress_text, progress_log, results_table)
        
        # Refresh progress manually
        def refresh_progress():
            if self.progress_tracker.is_running:
                return (
                    self.progress_tracker.current_message,
                    self.progress_tracker.get_log(),
                    self.get_current_results()
                )
            elif hasattr(self, '_current_results'):
                return (
                    "✅ Fetch completed - results available below",
                    self.progress_tracker.get_log(),
                    self.get_current_results()
                )
            else:
                return (
                    "No fetch in progress",
                    self.progress_tracker.get_log(),
                    self.get_current_results()
                )
        
        refresh_btn.click(
            fn=refresh_progress,
            outputs=[progress_text, progress_log, results_table]
        )
    
    def _setup_view_events(self, load_latest_btn, file_upload, team_selector,
                          team_summary, player_details, data_info):
        """Set up view tab events with optimization."""
        
        def load_latest():
            try:
                filepath = self.data_saver.get_latest_data_file()
                return self._process_data_file(filepath)
            except FileNotFoundError:
                empty_df = pd.DataFrame({"Message": ["No data files found"]})
                return empty_df, gr.Dropdown(choices=[]), ""
            except Exception as e:
                error_df = pd.DataFrame({"Error": [str(e)]})
                return error_df, gr.Dropdown(choices=[]), f"Error: {e}"
        
        def load_uploaded(file_path):
            if not file_path:
                return pd.DataFrame(), gr.Dropdown(choices=[]), ""
            return self._process_data_file(file_path)
        
        def show_team_players(team_id):
            if not hasattr(self, '_current_data') or not team_id:
                return pd.DataFrame()
            
            for team_data in self._current_data.get('teams', []):
                if team_data.get('team_id') == team_id:
                    players = team_data.get('players', [])
                    if not players:
                        return pd.DataFrame({"Message": ["No players found"]})
                    
                    # Convert to simple DataFrame
                    df_data = []
                    for player in players:
                        df_data.append({
                            'Name': player.get('name', 'Unknown'),
                            'Position': player.get('type', 'Unknown'),
                            'Jersey': player.get('jersey_number', ''),
                            'DOB': player.get('date_of_birth', ''),
                            'Height': player.get('height', ''),
                            'Weight': player.get('weight', '')
                        })
                    return pd.DataFrame(df_data)
            
            return pd.DataFrame({"Message": ["Team not found"]})
        
        # Simple event handlers
        load_latest_btn.click(
            fn=load_latest,
            outputs=[team_summary, team_selector, data_info]
        )
        
        file_upload.change(
            fn=load_uploaded,
            inputs=[file_upload],
            outputs=[team_summary, team_selector, data_info]
        )
        
        team_selector.change(
            fn=show_team_players,
            inputs=[team_selector],
            outputs=[player_details]
        )
    
    def _fetch_data_background(self, competition_id: str, season_id: str, 
                              filter_participation: bool):
        """Background data fetching with detailed progress tracking."""
        try:
            self.progress_tracker.update("🔍 Fetching season competitors from API...")
            
            # Get competitors
            competitors = self.endpoints.get_season_competitors(season_id)
            if not competitors:
                self.progress_tracker.update("❌ No competitors found for this season")
                return
            
            self.progress_tracker.update(f"✅ Found {len(competitors)} teams in season")
            teams_data = []
            
            # Process each team with detailed logging
            for i, competitor_item in enumerate(competitors):
                if 'competitor' in competitor_item:
                    competitor = competitor_item['competitor']
                else:
                    competitor = competitor_item
                
                comp_id = competitor.get('id')
                comp_name = competitor.get('name', 'Unknown')
                comp_abbr = competitor.get('abbreviation', 'N/A')
                
                self.progress_tracker.update(f"🏉 [{i+1}/{len(competitors)}] Fetching {comp_name} ({comp_abbr})...")
                
                try:
                    if filter_participation:
                        self.progress_tracker.update(f"🔍 Extracting players who actually played for {comp_name}...")
                        players = self.player_extractor.extract_players_from_season(season_id, comp_id)
                        if not players:
                            self.progress_tracker.update(f"⚠️ No match data found, falling back to full roster for {comp_name}")
                            profile = self.endpoints.get_competitor_profile(comp_id)
                            players_data = profile.get('players', [])
                            if not players_data and 'competitor' in profile:
                                players_data = profile.get('competitor', {}).get('players', [])
                            players = [Player.from_api_data(p) for p in players_data]
                    else:
                        self.progress_tracker.update(f"📋 Fetching full roster for {comp_name}...")
                        profile = self.endpoints.get_competitor_profile(comp_id)
                        players_data = profile.get('players', [])
                        if not players_data and 'competitor' in profile:
                            players_data = profile.get('competitor', {}).get('players', [])
                        players = [Player.from_api_data(p) for p in players_data]
                    
                    # Create team
                    team = Team(
                        id=comp_id,
                        name=comp_name,
                        abbreviation=comp_abbr,
                        players=players,
                        filtered_by_participation=filter_participation
                    )
                    
                    teams_data.append(team)
                    
                    if players:
                        self.progress_tracker.update(f"✅ {comp_name}: Found {len(players)} players")
                    else:
                        self.progress_tracker.update(f"⚠️ {comp_name}: No player data available")
                    
                except Exception as e:
                    self.progress_tracker.update(f"❌ Error processing {comp_name}: {str(e)}")
                    # Continue with other teams even if one fails
                    continue
            
            # Save results with detailed feedback
            if teams_data:
                self.progress_tracker.update("💾 Saving results to file...")
                filepath = self.data_saver.save_teams_data(
                    teams_data, competition_id, season_id, filter_participation
                )
                total_players = sum(team.player_count for team in teams_data)
                filename = os.path.basename(filepath)
                
                self.progress_tracker.update(f"🎉 Fetch completed successfully!")
                self.progress_tracker.update(f"📊 Results: {len(teams_data)} teams, {total_players} total players")
                self.progress_tracker.update(f"💾 Data saved as: {filename}")
                
                # Show team breakdown
                for team in teams_data:
                    self.progress_tracker.update(f"   • {team.name}: {team.player_count} players")
                
                # Store results for UI updates
                self._store_results_summary(teams_data)
            else:
                self.progress_tracker.update("❌ No team data was successfully collected")
                
        except Exception as e:
            self.progress_tracker.update(f"❌ Fatal error during fetch: {str(e)}")
            import traceback
            self.progress_tracker.update(f"Debug: {traceback.format_exc()}")
        finally:
            self.progress_tracker.is_running = False
    
    def _store_results_summary(self, teams_data: List[Team]) -> None:
        """Store results summary for UI updates."""
        results_data = []
        for team in teams_data:
            results_data.append({
                "Team": team.name,
                "Abbreviation": team.abbreviation,
                "Player Count": team.player_count,
                "Status": "✅ Completed" if team.player_count > 0 else "⚠️ No players"
            })
        
        # Store for later retrieval
        self._current_results = pd.DataFrame(results_data)
    
    def get_current_results(self) -> pd.DataFrame:
        """Get current results for UI display."""
        if hasattr(self, '_current_results'):
            return self._current_results
        return pd.DataFrame({
            "Team": ["No data fetched yet"],
            "Abbreviation": [""],
            "Player Count": [""],
            "Status": ["Click 'Fetch Player Data' to start"]
        })
    
    def _process_data_file(self, filepath: str) -> Tuple[pd.DataFrame, gr.Dropdown, str]:
        """Process a data file for viewing."""
        try:
            data = self.data_saver.load_teams_data(filepath)
            self._current_data = data
            
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
            
            # Create info text
            filename = os.path.basename(filepath)
            info_text = f"""Loaded: {filename}
Total Teams: {data.get('total_teams', 0)}
Total Players: {data.get('total_players', 0)}
Filtered: {'Yes' if data.get('filtered_by_participation') else 'No'}"""
            
            return summary_df, gr.Dropdown(choices=team_choices), info_text
            
        except Exception as e:
            error_df = pd.DataFrame({"Error": [f"Failed to load: {str(e)}"]})
            return error_df, gr.Dropdown(choices=[]), f"Error: {e}"
    
    def launch(self, **kwargs):
        """Launch the optimized interface."""
        return self.interface.launch(**kwargs)