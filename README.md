# Rugby Union Player Data Fetcher

A Gradio-based web application for fetching and filtering rugby player data from the Sportradar Rugby Union API.

## Features

- **Competition & Season Selection**: Browse all available rugby competitions and seasons
- **Smart Player Filtering**: Only returns players who actually participated in matches (not full squad rosters)  
- **Network Resilience**: Automatic retry logic with exponential backoff
- **Resume Capability**: Checkpoint system allows resuming interrupted data fetches
- **Multi-tier Data Extraction**: 
  - Uses match statistics for newer seasons (2023+)
  - Falls back to lineup data for older seasons (2022 and earlier)
- **Export Options**: Save data as JSON with timestamps
- **Data Visualization**: View fetched player data in an interactive table

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Key**:
   - Get a Sportradar Rugby Union API key
   - Create a `.env` file:
     ```
     SPORTRADAR_API_KEY=your_api_key_here
     ```

3. **Run the Application**:
   ```bash
   python gradio_rugby_ui.py
   ```
   
   Or with custom port range:
   ```bash
   python gradio_rugby_ui.py --start-port 7860 --end-port 7870
   ```

## Usage

### Fetch Data Tab
1. Select a competition from the dropdown
2. Choose a season
3. Pick specific competitors/teams or fetch all
4. Click "Fetch Player Data"
5. Monitor progress and download results

### View Data Tab  
- Upload and view previously exported JSON files
- Interactive table with search and filtering

## API Integration

Uses Sportradar Rugby Union API v3 with intelligent data extraction:

- **Recent Seasons**: Extracts player participation from match statistics
- **Older Seasons**: Uses lineup data to identify players who actually played
- **Fallback Strategy**: Multiple endpoints ensure comprehensive data coverage

## Key Files

- `gradio_rugby_ui.py` - Main Gradio application
- `fetch_all_rugby_players.py` - Core data fetching logic
- `requirements.txt` - Python dependencies

## Data Accuracy

The application specifically addresses the issue of getting full squad rosters instead of actual match participants by:

1. Checking match statistics for player participation data
2. Falling back to lineup endpoints for older seasons
3. Filtering players based on `played: true` status in lineups
4. Only returning players who actually participated in matches

This ensures accurate data for all seasons across different API data structures.