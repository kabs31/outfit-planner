"""
Simple HTTP server to serve our custom product catalog
Run this to create a local product API
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os

class CustomProductAPIHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/products':
            # Serve the products JSON
            json_path = os.path.join(os.path.dirname(__file__), 'app', 'data', 'custom_products.json')
            
            try:
                with open(json_path, 'r') as f:
                    products_data = json.load(f)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(products_data['products']).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

def run_server(port=9000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, CustomProductAPIHandler)
    print(f'✅ Custom Product API running on http://localhost:{port}')
    print(f'📦 Products available at: http://localhost:{port}/products')
    print(f'Press Ctrl+C to stop')
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
