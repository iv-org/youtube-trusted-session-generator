import asyncio
from nodriver import start, cdp, loop
import time
import json
import sys

async def main():
    browser = await start(headless=False)
    print("[INFO] launching browser.")
    tab = browser.main_tab
    tab.add_handler(cdp.network.RequestWillBeSent, send_handler)
    page = await browser.get('https://www.youtube.com/embed/jNQXAC9IVRw')
    await tab.wait(cdp.network.RequestWillBeSent)
    button_play = await tab.select("#movie_player")
    await button_play.click()
    await tab.wait(cdp.network.RequestWillBeSent)
    print("[INFO] waiting additional 30 seconds for slower connections.")
    await tab.sleep(30)

async def send_handler(event: cdp.network.RequestWillBeSent):
    if "/youtubei/v1/player" in event.request.url:
        post_data = event.request.post_data
        post_data_json = json.loads(post_data)
        print("visitor_data: " + post_data_json["context"]["client"]["visitorData"])
        print("po_token: " + post_data_json["serviceIntegrityDimensions"]["poToken"])
        sys.exit(0)
    return

if __name__ == '__main__':

    loop().run_until_complete(main())