"""
Player data extraction utilities.

Handles extracting player participation data from match lineups with multiple
fallback strategies for different API data structures.
"""

from typing import List, Dict, Set
from ..models.player import Player
from ..api.endpoints import RugbyEndpoints


class PlayerExtractor:
    """
    Extracts player participation data from rugby match lineups.
    
    Uses a multi-tier approach:
    1. Season lineups endpoint (most efficient)
    2. Individual match lineups (fallback)
    3. Match statistics (last resort)
    """
    
    def __init__(self, endpoints: RugbyEndpoints):
        """
        Initialize player extractor.
        
        Args:
            endpoints: RugbyEndpoints instance for API access
        """
        self.endpoints = endpoints
    
    def extract_players_from_season(self, season_id: str, competitor_id: str) -> List[Player]:
        """
        Extract all players who participated in matches for a team during a season.
        
        This method builds the player list directly from match lineup data,
        ensuring only players who actually played are included.
        
        Args:
            season_id: Sportradar season identifier
            competitor_id: Sportradar competitor identifier
            
        Returns:
            List[Player]: Players who participated in matches
        """
        # First try the efficient season lineups approach
        players = self._extract_from_season_lineups(season_id, competitor_id)
        
        if players:
            return players
        
        # Fall back to individual match checking
        self.endpoints.client.update_progress(
            "Season lineups not available, checking individual matches..."
        )
        return self._extract_from_individual_matches(season_id, competitor_id)
    
    def _extract_from_season_lineups(self, season_id: str, competitor_id: str) -> List[Player]:
        """
        Extract players using the season lineups endpoint.
        
        This is the most efficient method as it fetches all match lineups
        in a single API call.
        
        Args:
            season_id: Sportradar season identifier
            competitor_id: Sportradar competitor identifier
            
        Returns:
            List[Player]: Players who participated, or empty list if method fails
        """
        season_lineups = self.endpoints.get_season_lineups(season_id)
        
        if not season_lineups or 'lineups' not in season_lineups:
            return []
        
        lineups_list = season_lineups['lineups']
        self.endpoints.client.update_progress(
            f"Processing {len(lineups_list)} matches from season lineups"
        )
        
        players_dict = {}  # Use dict to avoid duplicates by player ID
        matches_processed = 0
        
        for match_data in lineups_list:
            # Each match has structure: {sport_event: {...}, lineups: {competitors: [...]}}
            if 'lineups' not in match_data or 'competitors' not in match_data['lineups']:
                continue
            
            competitors_lineups = match_data['lineups']['competitors']
            
            # Find our team in this match
            for comp_lineup in competitors_lineups:
                if comp_lineup.get('id') == competitor_id:
                    matches_processed += 1
                    players_data = comp_lineup.get('players', [])
                    
                    # Process each player in the lineup
                    for player_data in players_data:
                        player = Player.from_api_data(player_data)
                        
                        # Only include players who actually participated
                        if player.actually_played() and player.id not in players_dict:
                            players_dict[player.id] = player
                    
                    self.endpoints.client.update_progress(
                        f"Match {matches_processed}: Found {len(players_data)} players"
                    )
                    break
        
        players_list = list(players_dict.values())
        self.endpoints.client.update_progress(
            f"Extracted {len(players_list)} unique players from {matches_processed} matches"
        )
        
        return players_list
    
    def _extract_from_individual_matches(self, season_id: str, competitor_id: str) -> List[Player]:
        """
        Extract players by checking individual match lineups.
        
        This is a fallback method that checks each match individually.
        Less efficient due to multiple API calls but more reliable for
        some API configurations.
        
        Args:
            season_id: Sportradar season identifier
            competitor_id: Sportradar competitor identifier
            
        Returns:
            List[Player]: Players who participated
        """
        # Get season summaries to find matches
        summaries = self.endpoints.get_season_summaries(season_id)
        if not summaries or 'summaries' not in summaries:
            return []
        
        summaries_list = summaries['summaries']
        players_dict = {}
        matches_processed = 0
        
        self.endpoints.client.update_progress(
            f"Checking individual matches from {len(summaries_list)} total matches"
        )
        
        for summary in summaries_list:
            sport_event = summary.get('sport_event', {})
            competitors = sport_event.get('competitors', [])
            
            # Check if our team played in this match
            team_in_match = any(comp.get('id') == competitor_id for comp in competitors)
            
            if team_in_match:
                sport_event_id = sport_event.get('id')
                if sport_event_id:
                    # Get lineup for this specific match
                    lineup_data = self.endpoints.get_sport_event_lineups(sport_event_id)
                    
                    if lineup_data and 'lineups' in lineup_data:
                        lineups = lineup_data['lineups']
                        comp_lineups = lineups.get('competitors', [])
                        
                        # Find our team in the lineups
                        for comp_lineup in comp_lineups:
                            if comp_lineup.get('id') == competitor_id:
                                matches_processed += 1
                                players_data = comp_lineup.get('players', [])
                                
                                # Process players
                                for player_data in players_data:
                                    player = Player.from_api_data(player_data)
                                    
                                    if player.actually_played() and player.id not in players_dict:
                                        players_dict[player.id] = player
                                
                                self.endpoints.client.update_progress(
                                    f"Match {matches_processed}: Found {len(players_data)} players"
                                )
                                break
        
        players_list = list(players_dict.values())
        self.endpoints.client.update_progress(
            f"Extracted {len(players_list)} unique players from {matches_processed} matches"
        )
        
        return players_list
    
    def get_player_ids_set(self, season_id: str, competitor_id: str) -> Set[str]:
        """
        Get set of player IDs who participated in the season.
        
        Legacy method for backwards compatibility.
        
        Args:
            season_id: Sportradar season identifier
            competitor_id: Sportradar competitor identifier
            
        Returns:
            Set[str]: Set of player IDs
        """
        players = self.extract_players_from_season(season_id, competitor_id)
        return {player.id for player in players}