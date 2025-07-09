import http.server
import socketserver
import webbrowser
import os

PORT = 8000
FILENAME = "public_tv.html"  

os.chdir(os.path.dirname(os.path.abspath(__file__)))

webbrowser.open(f"http://localhost:{PORT}/{FILENAME}")

Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}/{FILENAME}")
    httpd.serve_forever()
