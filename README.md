# Rugby Union Player Data Fetcher

A professional, modular web application for fetching and analyzing rugby player data from the Sportradar Rugby Union API.

## ✨ Features

- **🏆 Competition & Season Selection**: Browse all available rugby competitions and seasons
- **🎯 Smart Player Filtering**: Only returns players who actually participated in matches (not full squad rosters)  
- **🔄 Network Resilience**: Automatic retry logic with exponential backoff
- **💾 Resume Capability**: Checkpoint system allows resuming interrupted data fetches
- **📊 Multi-tier Data Extraction**: 
  - Uses season lineups for efficient bulk fetching
  - Falls back to individual match lineups when needed
  - Handles different API data structures across seasons
- **📁 Export & Import**: Save/load data as JSON with comprehensive metadata
- **🔍 Interactive Data Visualization**: Explore player data with filtering and search

## 🏗️ Architecture

The application follows a clean, modular architecture:

```
rugby_union/
├── main.py                    # Application entry point
├── rugby_app/                 # Main application package
│   ├── config.py             # Configuration management
│   ├── models/               # Data models
│   │   ├── player.py         # Player data class
│   │   ├── team.py           # Team data class
│   │   └── checkpoint.py     # Resume functionality
│   ├── api/                  # API interaction layer
│   │   ├── client.py         # HTTP client with retries
│   │   └── endpoints.py      # Sportradar API endpoints
│   ├── utils/                # Utility functions
│   │   ├── player_extractor.py  # Player data extraction logic
│   │   ├── data_saver.py     # File I/O operations
│   │   └── port_finder.py    # Network utilities
│   └── ui/                   # User interface
│       └── gradio_interface.py  # Gradio web interface
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
Get your Sportradar Rugby Union API key and set it up:

**Option A: Environment file (recommended)**
```bash
# Create .env file
echo "SPORTRADAR_API_KEY=your_api_key_here" > .env
```

**Option B: Environment variable**
```bash
export SPORTRADAR_API_KEY=your_api_key_here
```

### 3. Run the Application
```bash
# Basic usage
python main.py

# With custom port
python main.py --port 8080

# With port range
python main.py --start-port 7860 --end-port 7870

# Create public share link
python main.py --share

# Don't open browser automatically
python main.py --no-browser
```

### 4. Use the Web Interface
1. **Fetch Data Tab**: Select competitions/seasons and fetch player data
2. **View Data Tab**: Load and explore previously saved data

## 📖 Usage Guide

### Fetching Data
1. Select a competition (e.g., "The Rugby Championship")
2. Choose a season (e.g., "2022")
3. Enable "Filter by actual participation" for accurate data
4. Click "Fetch Player Data"
5. Monitor progress and download results when complete

### Viewing Data
1. Use "Load Latest Data" or upload a JSON file
2. Select a team from the dropdown
3. Explore player details in the interactive table

## 🔧 Configuration

The application can be configured via:
- **Environment variables**: Set `SPORTRADAR_API_KEY` and other settings
- **Command line arguments**: Port, host, sharing options
- **Config file**: Modify `rugby_app/config.py` for advanced settings

## 🛡️ Error Handling

- **API Rate Limits**: Automatic retry with exponential backoff
- **Network Issues**: Connection pooling and timeout handling
- **Data Recovery**: Checkpoint system preserves progress
- **Graceful Degradation**: Fallback strategies for different API responses

## 📊 Data Structure

### Team Data
```json
{
  "team": "South Africa",
  "team_id": "sr:competitor:4231",
  "abbreviation": "RSA", 
  "player_count": 35,
  "players": [...],
  "filtered_by_participation": true
}
```

### Player Data
```json
{
  "id": "sr:player:500760",
  "name": "Kolisi, Siya",
  "type": "BR",
  "jersey_number": 6,
  "date_of_birth": "1991-06-16",
  "height": 186,
  "weight": 99,
  "played": true
}
```

## 🔌 API Integration

**Sportradar Rugby Union API v3**
- Primary endpoint: Season lineups for bulk data
- Fallback: Individual match lineups
- Error handling: Rate limits, timeouts, connection issues
- Data validation: Player participation filtering

## 🧪 Development

### Project Structure
- **Models**: Pure data classes with business logic
- **API Layer**: HTTP communication and endpoint management
- **Utils**: Reusable utility functions  
- **UI**: Gradio interface components
- **Config**: Centralized configuration management

### Adding Features
1. **New API endpoints**: Add to `rugby_app/api/endpoints.py`
2. **Data models**: Extend classes in `rugby_app/models/`
3. **UI components**: Modify `rugby_app/ui/gradio_interface.py`
4. **Utilities**: Add to `rugby_app/utils/`

## ⚠️ Known Limitations

- **Historical Data**: Sportradar API may not provide historically accurate lineups for older seasons (pre-2020)
- **Rate Limits**: API has request limits; application handles this with delays and retries
- **Data Availability**: Some competitions/seasons may have limited player statistics

## 🆘 Troubleshooting

### Common Issues
1. **"No API key configured"**: Set `SPORTRADAR_API_KEY` environment variable
2. **"Port not available"**: Use `--port` or `--start-port` arguments
3. **"No data files found"**: Run data fetch first or upload a JSON file
4. **Rate limit errors**: Application automatically handles these with retries

### Getting Help
- Check the detailed progress log in the web interface
- Verify API key is valid at [Sportradar Developer Portal](https://developer.sportradar.com/)
- Review error messages in the terminal output

## 📄 License

This project is open source. Please respect Sportradar's API terms of service.