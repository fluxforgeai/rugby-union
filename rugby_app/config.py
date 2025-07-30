"""
Configuration module for Rugby Union Player Data Fetcher.

Contains all configuration constants, API settings, and environment variable handling.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""
    
    # API Configuration
    SPORTRADAR_API_KEY: Optional[str] = os.getenv('SPORTRADAR_API_KEY')
    BASE_URL: str = "https://api.sportradar.com/rugby-union/trial/v3/en"
    
    # Rate limiting settings
    DELAY_BETWEEN_REQUESTS: int = 5  # seconds
    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 30  # seconds
    
    # Data processing settings
    MAX_MATCHES_TO_CHECK: int = 10  # Limit individual match checks to avoid rate limits
    
    # File paths
    OUTPUT_DIR: str = "rugby_data_output"
    CHECKPOINT_DIR: str = "rugby_data_checkpoints"
    
    # Default UI settings
    DEFAULT_PORT_RANGE: tuple = (7860, 7870)
    DEFAULT_HOST: str = "127.0.0.1"
    
    @classmethod
    def validate_api_key(cls) -> bool:
        """
        Validate that API key is present and not a placeholder.
        
        Returns:
            bool: True if API key is valid, False otherwise
        """
        return (
            cls.SPORTRADAR_API_KEY is not None 
            and cls.SPORTRADAR_API_KEY != 'your-sportradar-key-if-not-using-env'
            and len(cls.SPORTRADAR_API_KEY.strip()) > 0
        )
    
    @classmethod
    def get_api_params(cls) -> dict:
        """
        Get API parameters dictionary for requests.
        
        Returns:
            dict: Parameters dictionary with API key
        """
        return {"api_key": cls.SPORTRADAR_API_KEY}


# Export commonly used values
API_KEY = Config.SPORTRADAR_API_KEY
BASE_URL = Config.BASE_URL
DELAY_BETWEEN_REQUESTS = Config.DELAY_BETWEEN_REQUESTS