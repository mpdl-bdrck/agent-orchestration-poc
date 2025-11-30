#!/usr/bin/env python3
"""Test script to verify logo files are accessible"""
import os
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time

class LogoTestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/logo_dark.png':
            logo_path = Path('public/logo_dark.png')
            if logo_path.exists():
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(logo_path.stat().st_size))
                self.end_headers()
                with open(logo_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        elif self.path == '/favicon.png':
            favicon_path = Path('public/favicon.png')
            if favicon_path.exists():
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(favicon_path.stat().st_size))
                self.end_headers()
                with open(favicon_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    print("Testing logo file access...")
    print("Access logo at: http://localhost:8765/logo_dark.png")
    print("Access favicon at: http://localhost:8765/favicon.png")
    print("Press Ctrl+C to stop")
    
    server = HTTPServer(('localhost', 8765), LogoTestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
