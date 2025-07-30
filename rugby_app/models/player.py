"""
Player data model for rugby player information.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Player:
    """
    Represents a rugby player with all relevant information.
    
    Attributes:
        id: Sportradar unique player identifier
        name: Full player name (e.g., "Smith, John")
        first_name: Player's first name
        last_name: Player's last name
        position: Playing position abbreviation (e.g., "FH", "BR", "HO")
        jersey_number: Jersey number (0 if not assigned)
        date_of_birth: Birth date in YYYY-MM-DD format
        nationality: Player's nationality
        height: Height in centimeters
        weight: Weight in kilograms
        played: Whether player actually played in the match (for lineup data)
        starter: Whether player was in starting XV
    """
    
    id: str
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: str = "Unknown"
    jersey_number: int = 0
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    height: int = 0
    weight: int = 0
    played: Optional[bool] = None
    starter: bool = False
    
    @classmethod
    def from_api_data(cls, data: dict) -> 'Player':
        """
        Create Player instance from Sportradar API response data.
        
        Args:
            data: Dictionary containing player data from API
            
        Returns:
            Player: New Player instance
        """
        return cls(
            id=data.get('id', ''),
            name=data.get('name', 'Unknown'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            position=data.get('type', data.get('position', 'Unknown')),
            jersey_number=data.get('jersey_number', 0),
            date_of_birth=data.get('date_of_birth'),
            nationality=data.get('nationality'),
            height=data.get('height', 0),
            weight=data.get('weight', 0),
            played=data.get('played'),
            starter=data.get('starter', False)
        )
    
    def to_dict(self) -> dict:
        """
        Convert Player instance to dictionary for JSON serialization.
        
        Returns:
            dict: Player data as dictionary
        """
        return {
            'id': self.id,
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'type': self.position,  # Keep 'type' for API compatibility
            'jersey_number': self.jersey_number,
            'date_of_birth': self.date_of_birth,
            'nationality': self.nationality,
            'height': self.height,
            'weight': self.weight,
            'played': self.played,
            'starter': self.starter
        }
    
    def actually_played(self) -> bool:
        """
        Determine if player actually participated in the match.
        
        Uses the logic: include if played=True or played field is missing
        (missing field typically means substitute who entered the game).
        Only exclude if explicitly played=False.
        
        Returns:
            bool: True if player participated, False otherwise
        """
        return self.played != False  # Includes None (missing field) and True
    
    def __str__(self) -> str:
        """String representation of player."""
        return f"{self.name} (#{self.jersey_number}, {self.position})"