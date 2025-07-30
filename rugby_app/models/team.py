"""
Team data model for rugby team information.
"""

from dataclasses import dataclass, field
from typing import List, Dict
from collections import Counter

from .player import Player


@dataclass
class Team:
    """
    Represents a rugby team with players and metadata.
    
    Attributes:
        id: Sportradar unique team identifier
        name: Team name (e.g., "South Africa")
        abbreviation: Team abbreviation (e.g., "RSA")
        players: List of Player objects
        filtered_by_participation: Whether player list was filtered by actual match participation
        error_message: Error message if data retrieval failed
    """
    
    id: str
    name: str
    abbreviation: str = ""
    players: List[Player] = field(default_factory=list)
    filtered_by_participation: bool = False
    error_message: str = ""
    
    @property
    def player_count(self) -> int:
        """Get total number of players in team."""
        return len(self.players)
    
    @property
    def position_summary(self) -> Dict[str, int]:
        """
        Get summary of player positions.
        
        Returns:
            Dict[str, int]: Position abbreviation -> count mapping
        """
        positions = Counter()
        for player in self.players:
            positions[player.position] += 1
        return dict(positions)
    
    def get_players_by_position(self, position: str) -> List[Player]:
        """
        Get all players for a specific position.
        
        Args:
            position: Position abbreviation (e.g., "FH", "BR")
            
        Returns:
            List[Player]: Players matching the position
        """
        return [p for p in self.players if p.position == position]
    
    def get_starters(self) -> List[Player]:
        """
        Get starting XV players (jersey numbers 1-15).
        
        Returns:
            List[Player]: Starting players sorted by jersey number
        """
        starters = [p for p in self.players if 1 <= p.jersey_number <= 15]
        return sorted(starters, key=lambda p: p.jersey_number)
    
    def get_substitutes(self) -> List[Player]:
        """
        Get substitute players (jersey numbers 16-23).
        
        Returns:
            List[Player]: Substitute players sorted by jersey number
        """
        subs = [p for p in self.players if 16 <= p.jersey_number <= 23]
        return sorted(subs, key=lambda p: p.jersey_number)
    
    def to_dict(self) -> dict:
        """
        Convert Team instance to dictionary for JSON serialization.
        
        Returns:
            dict: Team data as dictionary
        """
        return {
            'team': self.name,
            'team_id': self.id,
            'abbreviation': self.abbreviation,
            'player_count': self.player_count,
            'position_summary': self.position_summary,
            'players': [player.to_dict() for player in self.players],
            'filtered_by_participation': self.filtered_by_participation,
            'error': self.error_message if self.error_message else None
        }
    
    @classmethod
    def from_api_data(cls, competitor_data: dict, players_data: List[dict], 
                      filtered_by_participation: bool = False) -> 'Team':
        """
        Create Team instance from Sportradar API response data.
        
        Args:
            competitor_data: Dictionary containing team/competitor data
            players_data: List of dictionaries containing player data
            filtered_by_participation: Whether players were filtered by participation
            
        Returns:
            Team: New Team instance
        """
        players = [Player.from_api_data(player_data) for player_data in players_data]
        
        return cls(
            id=competitor_data.get('id', ''),
            name=competitor_data.get('name', 'Unknown'),
            abbreviation=competitor_data.get('abbreviation', ''),
            players=players,
            filtered_by_participation=filtered_by_participation
        )
    
    def __str__(self) -> str:
        """String representation of team."""
        return f"{self.name} ({self.abbreviation}) - {self.player_count} players"