# Rugby Player Data Fetcher - Gradio UI

A web-based interface for fetching rugby player data from the Sportradar API.

## Features

- **Port Management**: Automatically finds available ports or use a specific port
- **Two-tab Interface**: 
  - Fetch Data: Select competition and season
  - View Data: Browse previously fetched data
- **Real-time Progress**: Live updates during data fetching
- **Background Processing**: Non-blocking data fetching

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
# Use default port range (8000-9000)
python gradio_rugby_ui.py

# Specify a custom port
python gradio_rugby_ui.py --port 8080

# Use a different port range
python gradio_rugby_ui.py --start-port 9000 --end-port 9999

# Run without opening browser
python gradio_rugby_ui.py --no-browser

# Create a public shareable link
python gradio_rugby_ui.py --share

# Use a different host
python gradio_rugby_ui.py --host 0.0.0.0
```

### Command Line Options

- `--port`: Specific port to use (will check availability)
- `--start-port`: Start of port range to search (default: 8000)
- `--end-port`: End of port range to search (default: 9000)
- `--host`: Host address (default: 127.0.0.1)
- `--no-browser`: Don't automatically open browser
- `--share`: Create a public shareable link

## Port Checking

The application will:
1. Check if the specified port is available (if using `--port`)
2. If not available or no port specified, search the port range
3. Automatically find and use the first available port
4. Display the selected port in the console

## Environment Setup

Create a `.env` file with your Sportradar API key:
```
SPORTRADAR_API_KEY=your-api-key-here
```

## Output

Fetched data is saved to the `rugby_data_output/` directory with timestamps.