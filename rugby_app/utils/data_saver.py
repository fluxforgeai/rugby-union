"""
Data saving utilities for rugby player data.

Handles saving data to JSON files with proper formatting and metadata.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from ..config import Config
from ..models.team import Team


class DataSaver:
    """
    Handles saving rugby data to JSON files with proper structure and metadata.
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize data saver.
        
        Args:
            output_dir: Directory to save files to (defaults to config setting)
        """
        self.output_dir = Path(output_dir or Config.OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
    
    def save_teams_data(self, teams: List[Team], competition_id: str, season_id: str,
                       filtered_by_participation: bool = False) -> str:
        """
        Save teams data to a JSON file with timestamp.
        
        Args:
            teams: List of Team objects to save
            competition_id: Sportradar competition identifier
            season_id: Sportradar season identifier
            filtered_by_participation: Whether data was filtered by participation
            
        Returns:
            str: Path to the saved file
        """
        # Generate timestamped filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"rugby_data_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # Prepare data structure
        data = {
            'generated_at': datetime.now().isoformat(),
            'competition_id': competition_id,
            'season_id': season_id,
            'filtered_by_participation': filtered_by_participation,
            'total_teams': len(teams),
            'total_players': sum(team.player_count for team in teams),
            'teams': [team.to_dict() for team in teams],
            'metadata': {
                'api_version': 'v3',
                'api_provider': 'Sportradar',
                'data_structure_version': '1.0'
            }
        }
        
        # Save to file with pretty formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def load_teams_data(self, filepath: str) -> Dict[str, Any]:
        """
        Load teams data from a JSON file.
        
        Args:
            filepath: Path to the JSON file to load
            
        Returns:
            Dict: Loaded data structure
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_latest_data_file(self) -> str:
        """
        Get the path to the most recently created data file.
        
        Returns:
            str: Path to latest file
            
        Raises:
            FileNotFoundError: If no data files exist
        """
        # Find all rugby data files
        pattern = "rugby_data_*.json"
        files = list(self.output_dir.glob(pattern))
        
        if not files:
            raise FileNotFoundError("No rugby data files found")
        
        # Sort by modification time (most recent first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return str(files[0])
    
    def list_data_files(self) -> List[Dict[str, Any]]:
        """
        List all available data files with metadata.
        
        Returns:
            List[Dict]: List of file information dictionaries
        """
        pattern = "rugby_data_*.json"
        files = list(self.output_dir.glob(pattern))
        
        file_info = []
        for filepath in files:
            try:
                # Get basic file info
                stat = filepath.stat()
                info = {
                    'filepath': str(filepath),
                    'filename': filepath.name,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
                
                # Try to get metadata from file
                try:
                    with open(filepath, 'r') as f:
                        # Read just the beginning to get metadata
                        data = json.load(f)
                        info.update({
                            'competition_id': data.get('competition_id'),
                            'season_id': data.get('season_id'),
                            'total_teams': data.get('total_teams', 0),
                            'total_players': data.get('total_players', 0),
                            'filtered_by_participation': data.get('filtered_by_participation', False)
                        })
                except:
                    # If we can't read the file, just use basic info
                    pass
                
                file_info.append(info)
                
            except Exception:
                # Skip files we can't read
                continue
        
        # Sort by modification time (most recent first)
        file_info.sort(key=lambda f: f['modified'], reverse=True)
        return file_info
    
    def cleanup_old_files(self, keep_count: int = 10) -> int:
        """
        Clean up old data files, keeping only the most recent ones.
        
        Args:
            keep_count: Number of recent files to keep
            
        Returns:
            int: Number of files deleted
        """
        files = list(self.output_dir.glob("rugby_data_*.json"))
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        deleted_count = 0
        for filepath in files[keep_count:]:
            try:
                filepath.unlink()
                deleted_count += 1
            except Exception:
                # Skip files we can't delete
                continue
        
        return deleted_count