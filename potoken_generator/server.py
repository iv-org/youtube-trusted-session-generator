import logging
from socketserver import ThreadingMixIn
from typing import Any, Callable, Dict, Optional, Tuple
from wsgiref.simple_server import WSGIServer, make_server

from potoken_generator.extractor import PotokenExtractor

logger = logging.getLogger('server')


class ThreadingWSGIServer(WSGIServer, ThreadingMixIn):
    """Thread per request HTTP server."""
    daemon_threads: bool = True


class PotokenServer:

    def __init__(self, potoken_extractor: PotokenExtractor, port: int = 8080, bind_address: str = '0.0.0.0') -> None:
        self.port = port
        self.bind_address = bind_address
        self._potoken_extractor = potoken_extractor
        self._httpd: Optional[ThreadingWSGIServer] = None

    def get_potoken(self) -> Tuple[str, list, str]:
        token = self._potoken_extractor.get()
        if token is None:
            status = '503 Service Unavailable'
            headers = [('Content-Type', 'text/plain')]
            page = 'Token has not yet been generated, try again later.'
        else:
            status = '200 OK'
            headers = [('Content-Type', 'application/json')]
            page = token.to_json()
        return status, headers, page

    def request_update(self) -> Tuple[str, list, str]:
        status = '200 OK'
        headers = [('Content-Type', 'text/plain')]

        accepted = self._potoken_extractor.request_update()
        if accepted:
            page = 'Update request accepted, new token will be generated soon.'
        else:
            page = 'Update has already been requested, new token will be generated soon.'

        return status, headers, page

    def get_route_handler(self, route: str) -> Callable[[], Tuple[str, list, str]]:
        handlers = {
            # handler is a function returning a tuple of status, headers, page text
            '/404': lambda: ('404 Not Found', [('Content-Type', 'text/plain')], 'Not Found'),
            '/': lambda: ('302 Found', [('Location', '/token')], '/token'),
            '/token': self.get_potoken,
            '/update': self.request_update
        }
        return handlers.get(route) or handlers['/404']

    def app(self, environ: Dict[str, Any], start_response):
        route = environ['PATH_INFO']

        handler = self.get_route_handler(route)
        status, headers, page = handler()

        start_response(status, headers)
        return [page.encode('utf8')]

    def run(self) -> None:
        logger.info(f'Starting web-server at {self.bind_address}:{self.port}')
        self._httpd = make_server(self.bind_address, self.port, self.app, ThreadingWSGIServer)
        with self._httpd:
            self._httpd.serve_forever()

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
