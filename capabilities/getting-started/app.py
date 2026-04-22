"""
Minimal HTTP server for the getting-started capability.
Serves index.html on a fixed port and prints the URL for Apollo to pick up.
"""

import http.server
import os
import socketserver
from pathlib import Path

PORT = 8766
ROOT = Path(__file__).parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format, *args):  # suppress request logs
        pass


if __name__ == "__main__":
    with socketserver.TCPServer(("localhost", PORT), Handler) as httpd:
        print(f"Server URL: http://localhost:{PORT}", flush=True)
        httpd.serve_forever()
