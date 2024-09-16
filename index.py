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
    print("[INFO] waiting 10 seconds for the page to fully load.")
    await tab.sleep(10)
    button_play = await tab.select("#movie_player")
    await button_play.click()
    await tab.wait(cdp.network.RequestWillBeSent)
    print("[INFO] waiting additional 30 seconds for slower connections.")
    await tab.sleep(30)

async def send_handler(event: cdp.network.RequestWillBeSent):
    if "/youtubei/v1/player" in event.request.url:
        post_data = event.request.post_data
        post_data_json = json.loads(post_data)
        visitor_data = post_data_json["context"]["client"]["visitorData"]
        po_token = post_data_json["serviceIntegrityDimensions"]["poToken"]
        print("visitor_data: " + visitor_data)
        print("po_token: " + po_token)
        if len(po_token) < 160:
            print("[WARNING] there is a high chance that the potoken generated won't work. please try again on another internet connection.")
        sys.exit(0)
    return

if __name__ == '__main__':

    loop().run_until_complete(main())