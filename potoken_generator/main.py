import argparse
import asyncio
import logging
import sys
from typing import Optional

import nodriver

from potoken_generator.extractor import PotokenExtractor, TokenInfo
from potoken_generator.server import PotokenServer

logger = logging.getLogger('potoken')


def print_token_and_exit(token_info: Optional[TokenInfo]):
    if token_info is None:
        logger.warning('failed to extract token')
        sys.exit(1)
    visitor_data = token_info.visitor_data
    po_token = token_info.potoken

    print('visitor_data: ' + visitor_data)
    print('po_token: ' + po_token)
    if len(po_token) < 160:
        logger.warning("there is a high chance that the potoken generated won't work. Please try again on another internet connection")
        sys.exit(1)
    sys.exit(0)


async def run(loop: asyncio.AbstractEventLoop, oneshot: bool,
              update_interval: int, bind_address: str, port: int) -> None:
    potoken_extractor = PotokenExtractor(loop, update_interval=update_interval)
    token = await potoken_extractor.run_once()
    if oneshot:
        print_token_and_exit(token)

    extractor_task = loop.create_task(potoken_extractor.run())
    potoken_server = PotokenServer(potoken_extractor, port=port, bind_address=bind_address)
    server_task = loop.create_task(asyncio.to_thread(potoken_server.run))

    try:
        await asyncio.gather(extractor_task, server_task)
    except Exception:
        # exceptions raised by the tasks are intentionally propogated
        # to ensure process exit code is 1 on error
        raise
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info('Stopping...')
    finally:
        potoken_server.stop()


def set_logging(log_level: int = logging.DEBUG) -> None:
    log_format = '%(asctime)s.%(msecs)03d [%(name)s] [%(levelname)s] %(message)s'
    datefmt = '%Y/%m/%d %H:%M:%S'
    logging.basicConfig(level=log_level, format=log_format, datefmt=datefmt)
    logging.getLogger('asyncio').setLevel(logging.INFO)
    logging.getLogger('nodriver').setLevel(logging.WARNING)
    logging.getLogger('uc').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)


def args_parse() -> argparse.Namespace:
    description = '''
Retrieve potoken using Chromium runned by nodriver, serve it on a json endpoint

    Token is generated on startup, and then every UPDATE_INTERVAL seconds.
    With web-server running on default port, the token is available on the
    http://127.0.0.1:8080/token endpoint. It is possible to request immediate
    token regeneration by accessing http://127.0.0.1:8080/update
    '''
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-o', '--oneshot', action='store_true', default=False,
                        help='Do not start server. Generate token once, print it and exit')
    parser.add_argument('--update-interval', '-u', type=int, default=3600,
                        help='How ofthen new token is generated, in seconds (default: %(default)s)')
    parser.add_argument('--port', '-p', type=int, default=8080,
                        help='Port webserver is listening on (default: %(default)s)')
    parser.add_argument('--bind', '-b', default='0.0.0.0',
                        help='Address webserver binds to (default: %(default)s)')
    return parser.parse_args()


def main() -> None:
    args = args_parse()
    set_logging(logging.WARNING if args.oneshot else logging.INFO)
    loop = nodriver.loop()
    main_task = run(loop, oneshot=args.oneshot, update_interval=args.update_interval, bind_address=args.bind, port=args.port)
    loop.run_until_complete(main_task)
