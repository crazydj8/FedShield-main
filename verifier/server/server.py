# server/server.py

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .verifier import Verifier

class VerificationHandler(BaseHTTPRequestHandler):
    def __init__(self, verifier: Verifier, *args, **kwargs):
        self.__verifier = verifier
        super().__init__(*args, **kwargs)
    
    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/verify':
            # Extract query parameters
            query_params = parse_qs(parsed_url.query)
            zkp_param = query_params.get('zkp', [None])[0]
            zkp_param_value = [True if zkp_param == "True" else False][0]
            
            # Extract body contents
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            # Send it to verifier for verification
            verification_result = self.__verifier.verify(data, zkp_param_value)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(verification_result).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()