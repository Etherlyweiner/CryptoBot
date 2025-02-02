from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        SimpleHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

# Change to the static directory
os.chdir('static')

# Start the server
server_address = ('localhost', 8000)
httpd = HTTPServer(server_address, CORSRequestHandler)
print(f"Server running at http://localhost:8000/")
print("Opening trading.html in your browser...")
os.system('start http://localhost:8000/trading.html')
httpd.serve_forever()
