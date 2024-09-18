import logging
import sys

import nodriver

from potoken import PotokenExtractor, set_logging


async def main(loop):
    set_logging(logging.WARNING)
    logger = logging.getLogger('index')

    extractor = PotokenExtractor(loop)
    token_info = await extractor.run_once()
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


if __name__ == '__main__':
    loop = nodriver.loop()
    loop.run_until_complete(main(loop))
