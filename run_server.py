import http.server
import socketserver
import os
import sys
from pathlib import Path

def run_server():
    # Get the absolute path to the static directory
    static_dir = Path(__file__).parent / 'static'
    
    # Verify static directory exists
    if not static_dir.exists():
        print(f"Error: Static directory not found at {static_dir}")
        sys.exit(1)
    
    # Change to static directory
    os.chdir(static_dir)
    print(f"Serving files from: {static_dir}")
    
    # Server configuration
    PORT = 8000
    HOSTNAME = "localhost"
    
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            print(f"Received request for: {self.path}")
            return super().do_GET()
            
        def log_message(self, format, *args):
            print(f"[Server] {format%args}")
    
    try:
        with socketserver.TCPServer((HOSTNAME, PORT), CustomHandler) as httpd:
            print(f"Server started at http://{HOSTNAME}:{PORT}")
            print(f"Open http://{HOSTNAME}:{PORT}/trading.html in your browser")
            print("Press Ctrl+C to stop the server")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 10048:  # Port already in use
            print(f"Error: Port {PORT} is already in use. Please close any other servers and try again.")
        else:
            print(f"Error starting server: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_server()
