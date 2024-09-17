import argparse
import asyncio
import json
import logging
import time
from socketserver import ThreadingMixIn
from tempfile import mkdtemp
from typing import Callable, Optional, Tuple
from wsgiref.simple_server import WSGIServer, make_server

import nodriver

logger = logging.getLogger('potoken')


class PotokenExtractor:

    def __init__(self, loop: asyncio.AbstractEventLoop, update_interfal: float = 3600 * 12) -> None:
        self.update_interval: float = update_interfal
        self.profile_path = mkdtemp()  # cleaned up on exit by nodriver
        self._loop = loop
        self._token_info: Optional[dict] = None
        self._ongoing_update: asyncio.Lock = asyncio.Lock()
        self._extraction_done: asyncio.Event = asyncio.Event()
        self._update_requested: asyncio.Event = asyncio.Event()

    def get(self) -> Optional[dict]:
        return self._token_info

    async def run_once(self) -> Optional[dict]:
        await self._update()
        return self.get()

    async def run(self):
        await self._update()
        while True:
            try:
                await asyncio.wait_for(self._update_requested.wait(), timeout=self.update_interval)
                logger.debug('initiating force update')
            except asyncio.TimeoutError:
                logger.debug('initiating scheduled update')
            await self._update()
            self._update_requested.clear()

    def request_update(self) -> bool:
        """Request immediate update, return False if update request is already set"""
        if self._ongoing_update.locked():
            logger.debug('update process is already running')
            return False
        if self._update_requested.is_set():
            logger.debug('force update has already been requested')
            return False
        self._loop.call_soon_threadsafe(self._update_requested.set)
        logger.debug('force update requested')
        return True

    @staticmethod
    def _extract_token(request: nodriver.cdp.network.Request) -> Optional[dict]:
        post_data = request.post_data
        try:
            post_data_json = json.loads(post_data)
            visitor_data = post_data_json['context']['client']['visitorData']
            potoken = post_data_json['serviceIntegrityDimensions']['poToken']
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f'failed to extract token from request: {type(e)}, {e}')
            return None
        token_info = {
            'updated': int(time.time()),
            'potoken': potoken,
            'visitor_data': visitor_data
        }
        return token_info

    async def _update(self) -> None:
        try:
            await asyncio.wait_for(self._perform_update(), timeout=600)
        except asyncio.TimeoutError:
            logger.error(f'update failed: hard limit timeout exceeded. Browser might be failing to start properly')

    async def _perform_update(self) -> None:
        if self._ongoing_update.locked():
            logger.debug('update is already in progress')
            return

        async with self._ongoing_update:
            logger.info(f'update started')
            self._extraction_done.clear()

            browser = await nodriver.start(headless=False, user_data_dir=self.profile_path)
            tab = browser.main_tab
            tab.add_handler(nodriver.cdp.network.RequestWillBeSent, self._send_handler)
            await tab.get('https://www.youtube.com/embed/jNQXAC9IVRw')
            player_clicked = await self._click_on_player(tab)
            if player_clicked:
                await self._wait_for_handler()
            await tab.close()
            browser.stop()

    @staticmethod
    async def _click_on_player(tab) -> bool:
        try:
            player = await tab.select("#movie_player", 10)
        except asyncio.TimeoutError:
            logger.warning(f'update failed: unable to locate video player on the page')
            return False
        else:
            await player.click()
            return True

    async def _wait_for_handler(self) -> bool:
        try:
            await asyncio.wait_for(self._extraction_done.wait(), timeout=30)
        except asyncio.TimeoutError:
            logger.warning(f'update failed: timeout waiting for outgoing API request')
            return False
        else:
            logger.info('update was succeessful')
            return True

    async def _send_handler(self, event: nodriver.cdp.network.RequestWillBeSent):
        if not event.request.method == 'POST':
            return
        if not '/youtubei/v1/player' in event.request.url:
            return
        token_info = self._extract_token(event.request)
        if token_info is None:
            return
        logger.info(f'new token: {token_info}')
        self._token_info = token_info
        self._extraction_done.set()


class ThreadingWSGIServer(WSGIServer, ThreadingMixIn):
    """Thread per request HTTP server."""
    daemon_threads = True


class PotokenServer:

    def __init__(self, potoken_extractor: PotokenExtractor, port: int = 8080, bind_address: str = '0.0.0.0'):
        self.port = port
        self.bind_address = bind_address
        self._potoken_extractor = potoken_extractor
        self._httpd: Optional[ThreadingWSGIServer] = None

    def get_potoken(self) -> Tuple[str, list, str]:
        token = self._potoken_extractor.get()
        if token is None:
            status = '502 Bad Gateway'
            headers = [("Content-Type", "text/plain")]
            page = 'Token has not yet been generated, try again later.'
        else:
            status = '200 OK'
            headers = [("Content-Type", "application/json")]
            page = json.dumps(token)
        return status, headers, page

    def request_update(self) -> Tuple[str, list, str]:
        status = '200 OK'
        headers = [("Content-Type", "text/plain")]

        accepted = self._potoken_extractor.request_update()
        if accepted:
            page = 'Update request accepted, new token will be generated soon.'
        else:
            page = 'Update has already been requested, new token will be generated soon.'

        return status, headers, page

    def get_route_handler(self, route: str) -> Callable[[], Tuple[str, list, str]]:
        handlers = {
            # handler is a function returning a tuple of status, headers, page text
            '/404': lambda: ('404 Not Found', [("Content-Type", "text/plain")], 'Not Found'),
            '/': lambda: ('302 Found', [('Location', '/token')], '/token'),
            '/token': self.get_potoken,
            '/update': self.request_update
        }
        return handlers.get(route) or handlers['/404']

    def app(self, environ, start_response):
        route = environ['PATH_INFO']

        handler = self.get_route_handler(route)
        status, headers, page = handler()

        start_response(status, headers)
        return [page.encode('utf8')]

    def run(self):
        logger.info(f'Starting web-server at {self.bind_address}:{self.port}')
        self._httpd = make_server(self.bind_address, self.port, self.app, ThreadingWSGIServer)
        with self._httpd:
            self._httpd.serve_forever()

    def stop(self):
        if self._httpd is None:
            return
        self._httpd.shutdown()


def main(update_interval, bind_address, port) -> None:
    loop = nodriver.loop()

    potoken_extractor = PotokenExtractor(loop, update_interfal=update_interval)
    potoken_server = PotokenServer(potoken_extractor, port=port, bind_address=bind_address)

    extractor_task = loop.create_task(potoken_extractor.run())
    server_task = loop.create_task(asyncio.to_thread(potoken_server.run))

    try:
        main_task = asyncio.gather(extractor_task, server_task)
        loop.run_until_complete(main_task)
    except Exception:
        # exceptions raised by the tasks are intentionally propogated
        # to ensure process exit code is 1 on error
        raise
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info('Stopping...')
    finally:
        potoken_server.stop()


def set_logging(log_level=logging.DEBUG):
    log_format = '%(asctime)s.%(msecs)03d [%(name)s] [%(levelname)s] %(message)s'
    datefmt = '%Y/%m/%d %H:%M:%S'
    logging.basicConfig(level=log_level, format=log_format, datefmt=datefmt)
    logging.getLogger('asyncio').setLevel(logging.INFO)
    logging.getLogger('nodriver').setLevel(logging.WARNING)
    logging.getLogger('uc').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)


def args_parse():
    description = '''
Retrieve potoken using Chromium runned by nodriver, serve it on a json endpoint

    Token is generated on startup, and then every UPDATE_INTERVAL seconds.
    With web-server running on default port, the token is available on the
    http://127.0.0.1:8080/token endpoint. It is possible to request immediate
    token regeneration by accessing http://127.0.0.1:8080/update
    '''
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--update-interval', '-u', type=int, default=3600 * 12,
                        help='How ofthen new token is generated, in seconds (default: %(default)s)')
    parser.add_argument('--port', '-p', type=int, default=8080,
                        help='Port webserver is listening on (default: %(default)s)')
    parser.add_argument('--bind', '-b', default='0.0.0.0',
                        help='Address webserver binds to (default: %(default)s)')
    return parser.parse_args()


if __name__ == '__main__':
    set_logging()
    args = args_parse()
    main(update_interval=args.update_interval, bind_address=args.bind, port=args.port)
