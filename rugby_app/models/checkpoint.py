"""
Checkpoint model for resumable data fetching operations.
"""

import pickle
import os
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field

from ..config import Config


@dataclass
class FetchCheckpoint:
    """
    Manages checkpoint data for resumable data fetching operations.
    
    Allows the application to resume fetching data after interruptions
    (network errors, rate limits, application restarts) by saving progress
    after each team is processed.
    
    Attributes:
        competition_id: Sportradar competition identifier
        season_id: Sportradar season identifier
        filter_participation: Whether to filter players by actual participation
        completed_teams: Set of team IDs that have been successfully processed
        all_teams_data: List of team data dictionaries
        total_players: Running total of players across all teams
        checkpoint_file: Path to the checkpoint file
    """
    
    competition_id: str
    season_id: str
    filter_participation: bool
    completed_teams: Set[str] = field(default_factory=set)
    all_teams_data: List[Dict] = field(default_factory=list)
    total_players: int = 0
    checkpoint_file: Path = field(init=False)
    
    def __post_init__(self):
        """Initialize checkpoint file path after instance creation."""
        # Create checkpoint directory if it doesn't exist
        os.makedirs(Config.CHECKPOINT_DIR, exist_ok=True)
        
        # Generate unique filename based on competition and season
        filename = f"checkpoint_{self.competition_id}_{self.season_id}.pkl"
        self.checkpoint_file = Path(Config.CHECKPOINT_DIR) / filename
    
    def save(self) -> None:
        """
        Save current checkpoint state to disk.
        
        Saves the checkpoint using pickle for fast serialization/deserialization.
        This allows resuming the exact state after interruptions.
        """
        try:
            with open(self.checkpoint_file, 'wb') as f:
                pickle.dump(self, f)
        except Exception as e:
            print(f"Warning: Could not save checkpoint: {e}")
    
    @classmethod
    def load(cls, competition_id: str, season_id: str) -> Optional['FetchCheckpoint']:
        """
        Load existing checkpoint from disk if it exists.
        
        Args:
            competition_id: Sportradar competition identifier
            season_id: Sportradar season identifier
            
        Returns:
            FetchCheckpoint: Loaded checkpoint or None if not found/invalid
        """
        # Create temporary instance to get file path
        temp_checkpoint = cls(competition_id, season_id, False)
        checkpoint_file = temp_checkpoint.checkpoint_file
        
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'rb') as f:
                    checkpoint = pickle.load(f)
                
                # Verify checkpoint matches current parameters
                if (checkpoint.competition_id == competition_id and 
                    checkpoint.season_id == season_id):
                    return checkpoint
                else:
                    print("Checkpoint found but doesn't match current parameters")
                    
            except Exception as e:
                print(f"Warning: Could not load checkpoint: {e}")
        
        return None
    
    def cleanup(self) -> None:
        """
        Remove checkpoint file after successful completion.
        
        Should be called when data fetching is completely finished
        to clean up temporary files.
        """
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                print("Checkpoint cleaned up successfully")
        except Exception as e:
            print(f"Warning: Could not clean up checkpoint: {e}")
    
    def get_progress_summary(self) -> str:
        """
        Get human-readable progress summary.
        
        Returns:
            str: Progress summary string
        """
        return (f"Processed {len(self.completed_teams)} teams, "
                f"found {self.total_players} total players")
    
    def __str__(self) -> str:
        """String representation of checkpoint."""
        return (f"Checkpoint({self.competition_id}, {self.season_id}) - "
                f"{self.get_progress_summary()}")