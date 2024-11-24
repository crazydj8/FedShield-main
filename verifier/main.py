from http.server import HTTPServer
from functools import partial

from server import VerificationHandler
from server import Verifier

def run(server_class: HTTPServer = HTTPServer, handler_class: VerificationHandler = VerificationHandler, port: int = 5000):
    verifier = Verifier()
    handler = partial(handler_class, verifier)
    server_address = ('', port)
    httpd = server_class(server_address, handler)
    print('Verifier is Listening on http://localhost:5000/...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()