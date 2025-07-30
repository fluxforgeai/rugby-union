"""
Rugby Union Player Data Fetcher - Main Application

A Gradio-based web application for fetching and analyzing rugby player data
from the Sportradar Rugby Union API.

Features:
- Competition and season selection
- Smart player filtering (actual participants vs full rosters)
- Network resilience with automatic retries
- Resume capability with checkpoints
- Data export and visualization

Usage:
    python main.py [options]

Options:
    --port PORT              Specific port to use
    --start-port START_PORT  Start of port range to try
    --end-port END_PORT      End of port range to try  
    --host HOST              Host address (default: 127.0.0.1)
    --no-browser            Don't open browser automatically
    --share                 Create public shareable link
"""

import argparse
import sys
import os
from pathlib import Path

# Add the current directory to Python path so we can import rugby_app
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from rugby_app.config import Config
from rugby_app.api.client import RugbyAPIClient
from rugby_app.api.endpoints import RugbyEndpoints
from rugby_app.utils.port_finder import find_available_port
from rugby_app.ui.gradio_interface import RugbyDataInterface


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Rugby Union Player Data Fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                          # Use default settings
    python main.py --port 8080              # Use specific port
    python main.py --start-port 7860 --end-port 7870  # Port range
    python main.py --share                  # Create public link
        """
    )
    
    # Port configuration
    port_group = parser.add_mutually_exclusive_group()
    port_group.add_argument(
        '--port', 
        type=int, 
        help='Specific port to use for the web interface'
    )
    port_group.add_argument(
        '--start-port',
        type=int,
        default=Config.DEFAULT_PORT_RANGE[0],
        help=f'Start of port range to try (default: {Config.DEFAULT_PORT_RANGE[0]})'
    )
    
    parser.add_argument(
        '--end-port',
        type=int, 
        default=Config.DEFAULT_PORT_RANGE[1],
        help=f'End of port range to try (default: {Config.DEFAULT_PORT_RANGE[1]})'
    )
    
    # Network configuration
    parser.add_argument(
        '--host',
        default=Config.DEFAULT_HOST,
        help=f'Host address to bind to (default: {Config.DEFAULT_HOST})'
    )
    
    # UI options
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help="Don't automatically open browser"
    )
    
    parser.add_argument(
        '--share',
        action='store_true',
        help='Create a public shareable link (Gradio share feature)'
    )
    
    return parser.parse_args()


def validate_environment():
    """
    Validate that the environment is properly configured.
    
    Returns:
        bool: True if environment is valid
    """
    if not Config.validate_api_key():
        print("❌ ERROR: Sportradar API key not found or invalid!")
        print()
        print("Please set your API key in one of these ways:")
        print("1. Create a .env file with: SPORTRADAR_API_KEY=your_key_here")
        print("2. Set environment variable: export SPORTRADAR_API_KEY=your_key_here")
        print()
        print("Get your API key from: https://developer.sportradar.com/")
        return False
    
    return True


def find_port(args):
    """
    Find an available port based on command line arguments.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Available port number
        
    Raises:
        SystemExit: If no available port found
    """
    if args.port:
        # User specified exact port
        if find_available_port(args.port, args.port):
            return args.port
        else:
            print(f"❌ ERROR: Port {args.port} is not available!")
            sys.exit(1)
    else:
        # Find available port in range
        port = find_available_port(args.start_port, args.end_port)
        if port:
            print(f"🔍 Found available port: {port}")
            return port
        else:
            print(f"❌ ERROR: No available ports in range {args.start_port}-{args.end_port}!")
            sys.exit(1)


def main():
    """Main application entry point."""
    print("🏉 Rugby Union Player Data Fetcher")
    print("=" * 50)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    print("✅ API key validated")
    
    # Find available port
    port = find_port(args)
    
    # Create output directories
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(Config.CHECKPOINT_DIR, exist_ok=True)
    
    print(f"📁 Data will be saved to: {Config.OUTPUT_DIR}")
    print(f"💾 Checkpoints will be saved to: {Config.CHECKPOINT_DIR}")
    
    try:
        # Initialize application components
        print("🔧 Initializing application...")
        
        # Create progress callback for API client
        def update_progress(message: str):
            print(f"API: {message}")
        
        # Initialize API components
        api_client = RugbyAPIClient(update_progress_callback=update_progress)
        endpoints = RugbyEndpoints(api_client)
        
        # Initialize UI
        interface = RugbyDataInterface(endpoints)
        
        print("🚀 Starting web interface...")
        print(f"📱 Interface will be available at: http://{args.host}:{port}")
        
        if not args.no_browser:
            print("🌐 Browser will open automatically")
        
        if args.share:
            print("🔗 Creating public shareable link...")
        
        print()
        print("Press Ctrl+C to stop the application")
        print("=" * 50)
        
        # Launch Gradio interface
        interface.launch(
            server_name=args.host,
            server_port=port,
            share=args.share,
            inbrowser=not args.no_browser,
            show_error=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Application error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            if 'api_client' in locals():
                api_client.close()
        except:
            pass


if __name__ == "__main__":
    main()