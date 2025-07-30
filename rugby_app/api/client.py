"""
HTTP client for Sportradar Rugby Union API.

Handles all HTTP requests with proper error handling, rate limiting, and retries.
"""

import time
import requests
from typing import Optional, Dict, Any, Callable
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import Config


class RugbyAPIClient:
    """
    HTTP client for Sportradar Rugby Union API with built-in resilience features.
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limiting protection
    - Request timeout handling
    - Connection pooling
    - Comprehensive error handling
    """
    
    def __init__(self, update_progress_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the API client.
        
        Args:
            update_progress_callback: Optional callback function for progress updates
        """
        self.base_url = Config.BASE_URL
        self.api_key = Config.SPORTRADAR_API_KEY
        self.delay = Config.DELAY_BETWEEN_REQUESTS
        self.max_retries = Config.MAX_RETRIES
        self.timeout = Config.REQUEST_TIMEOUT
        self.update_progress = update_progress_callback or self._default_progress_callback
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _default_progress_callback(self, message: str) -> None:
        """Default progress callback that prints to console."""
        print(f"API: {message}")
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
        """
        Make HTTP request to Sportradar API with resilience features.
        
        Args:
            endpoint: API endpoint path (e.g., "/competitions.json")
            params: Additional query parameters
            
        Returns:
            requests.Response: Response object or None if request failed
        """
        # Prepare request parameters
        request_params = Config.get_api_params()
        if params:
            request_params.update(params)
        
        url = f"{self.base_url}{endpoint}"
        
        # Rate limiting: wait before making request
        if self.delay > 0:
            self.update_progress(f"Waiting {self.delay} seconds before API call...")
            time.sleep(self.delay)
        
        # Make request with retries
        for attempt in range(self.max_retries + 1):
            try:
                self.update_progress(f"Making request to {endpoint} (attempt {attempt + 1})")
                
                response = self.session.get(
                    url,
                    params=request_params,
                    timeout=self.timeout
                )
                
                # Check response status
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    # Rate limited - wait longer and retry
                    wait_time = (attempt + 1) * self.delay * 2
                    self.update_progress(f"Rate limited (429). Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    self.update_progress(f"API error {response.status_code}: {response.text[:200]}")
                    if attempt == self.max_retries:
                        return None
                    
            except requests.exceptions.Timeout:
                self.update_progress(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.max_retries:
                    return None
                    
            except requests.exceptions.ConnectionError as e:
                self.update_progress(f"Connection error on attempt {attempt + 1}: {str(e)[:100]}")
                if attempt == self.max_retries:
                    return None
                    
            except Exception as e:
                self.update_progress(f"Unexpected error on attempt {attempt + 1}: {str(e)[:100]}")
                if attempt == self.max_retries:
                    return None
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                wait_time = self.delay * (2 ** attempt)
                self.update_progress(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        return None
    
    def get_json(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Make API request and return JSON response.
        
        Args:
            endpoint: API endpoint path
            params: Additional query parameters
            
        Returns:
            dict: Parsed JSON response or None if request failed
        """
        response = self._make_request(endpoint, params)
        
        if response and response.status_code == 200:
            try:
                return response.json()
            except ValueError as e:
                self.update_progress(f"Failed to parse JSON response: {e}")
                return None
        
        return None
    
    def close(self) -> None:
        """Close the HTTP session and clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()