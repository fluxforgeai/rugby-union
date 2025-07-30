"""
Sportradar Rugby Union API endpoints wrapper.

Provides high-level methods for accessing specific API endpoints with proper
error handling and data validation.
"""

from typing import List, Dict, Optional, Any

from .client import RugbyAPIClient


class RugbyEndpoints:
    """
    High-level wrapper for Sportradar Rugby Union API endpoints.
    
    Provides convenient methods for accessing rugby data with built-in
    error handling and progress reporting.
    """
    
    def __init__(self, client: RugbyAPIClient):
        """
        Initialize endpoints wrapper.
        
        Args:
            client: Configured RugbyAPIClient instance
        """
        self.client = client
    
    def get_competitions(self) -> List[Dict[str, Any]]:
        """
        Get all available rugby competitions.
        
        Returns:
            List[Dict]: List of competition dictionaries with id and name
        """
        self.client.update_progress("Fetching competitions...")
        
        data = self.client.get_json("/competitions.json")
        if data and 'competitions' in data:
            return data['competitions']
        
        self.client.update_progress("Failed to fetch competitions")
        return []
    
    def get_competition_seasons(self, competition_id: str) -> List[Dict[str, Any]]:
        """
        Get all seasons for a specific competition.
        
        Args:
            competition_id: Sportradar competition identifier
            
        Returns:
            List[Dict]: List of season dictionaries
        """
        self.client.update_progress("Fetching seasons...")
        
        endpoint = f"/competitions/{competition_id}/seasons.json"
        data = self.client.get_json(endpoint)
        
        if data and 'seasons' in data:
            return data['seasons']
        
        self.client.update_progress("Failed to fetch seasons")
        return []
    
    def get_season_competitors(self, season_id: str) -> List[Dict[str, Any]]:
        """
        Get all teams/competitors in a season.
        
        Args:
            season_id: Sportradar season identifier
            
        Returns:
            List[Dict]: List of competitor dictionaries
        """
        self.client.update_progress("Fetching competitors...")
        
        endpoint = f"/seasons/{season_id}/competitors.json"
        data = self.client.get_json(endpoint)
        
        if data and 'season_competitors' in data:
            return data['season_competitors']
        
        self.client.update_progress("Failed to fetch competitors")
        return []
    
    def get_season_summaries(self, season_id: str) -> Dict[str, Any]:
        """
        Get season summaries including all matches.
        
        Args:
            season_id: Sportradar season identifier
            
        Returns:
            Dict: Season summaries data
        """
        self.client.update_progress("Fetching season match summaries...")
        
        endpoint = f"/seasons/{season_id}/summaries.json"
        data = self.client.get_json(endpoint)
        
        if data:
            return data
        
        self.client.update_progress("Failed to fetch season summaries")
        return {}
    
    def get_season_lineups(self, season_id: str) -> Dict[str, Any]:
        """
        Get all match lineups for a season.
        
        This endpoint provides comprehensive lineup data for all matches
        in the season, including player participation information.
        
        Args:
            season_id: Sportradar season identifier
            
        Returns:
            Dict: Season lineups data with structure:
                {
                    "lineups": [
                        {
                            "sport_event": {...},
                            "lineups": {
                                "competitors": [
                                    {
                                        "id": "sr:competitor:xxx",
                                        "name": "Team Name",
                                        "players": [...]
                                    }
                                ]
                            }
                        }
                    ]
                }
        """
        self.client.update_progress("Fetching season lineups...")
        
        endpoint = f"/seasons/{season_id}/lineups.json"
        data = self.client.get_json(endpoint)
        
        if data:
            return data
        
        self.client.update_progress("Failed to fetch season lineups")
        return {}
    
    def get_season_players(self, season_id: str) -> Dict[str, Any]:
        """
        Get all players participating in a season.
        
        Note: This endpoint returns all players from all teams in the season
        but doesn't include team affiliation information.
        
        Args:
            season_id: Sportradar season identifier
            
        Returns:
            Dict: Season players data
        """
        self.client.update_progress("Fetching season players...")
        
        endpoint = f"/seasons/{season_id}/players.json"
        data = self.client.get_json(endpoint)
        
        if data:
            return data
        
        self.client.update_progress("Failed to fetch season players")
        return {}
    
    def get_competitor_profile(self, competitor_id: str) -> Dict[str, Any]:
        """
        Get competitor profile including full team roster.
        
        Args:
            competitor_id: Sportradar competitor identifier
            
        Returns:
            Dict: Competitor profile data including players list
        """
        endpoint = f"/competitors/{competitor_id}/profile.json"
        data = self.client.get_json(endpoint)
        
        if data:
            return data
        
        self.client.update_progress(f"Failed to fetch competitor profile for {competitor_id}")
        return {}
    
    def get_sport_event_summary(self, sport_event_id: str) -> Dict[str, Any]:
        """
        Get sport event summary including match statistics.
        
        Args:
            sport_event_id: Sportradar sport event identifier
            
        Returns:
            Dict: Sport event summary data
        """
        endpoint = f"/sport_events/{sport_event_id}/summary.json"
        data = self.client.get_json(endpoint)
        
        if data:
            return data
        
        return {}
    
    def get_sport_event_lineups(self, sport_event_id: str) -> Dict[str, Any]:
        """
        Get lineups for a specific sport event/match.
        
        Args:
            sport_event_id: Sportradar sport event identifier
            
        Returns:
            Dict: Sport event lineups data
        """
        endpoint = f"/sport_events/{sport_event_id}/lineups.json"
        data = self.client.get_json(endpoint)
        
        if data:
            return data
        
        return {}