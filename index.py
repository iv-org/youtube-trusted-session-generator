import asyncio
from nodriver import start, cdp, loop
import time
import json
import sys
import customtkinter as ct

app = ct.CTk()
app.geometry("440x330")
app.title("YouTube Trusted Session generator")


browser = None

async def main():
    global browser
    browser = await start(headless=False)
    print("[INFO] launching browser.")
    tab = browser.main_tab
    tab.add_handler(cdp.network.RequestWillBeSent, send_handler)
    await browser.get('https://www.youtube.com/embed/jNQXAC9IVRw')
    await tab.wait(cdp.network.RequestWillBeSent)
    button_play = await tab.select("#movie_player")
    await button_play.click()
    await tab.wait(cdp.network.RequestWillBeSent)
    print("[INFO] waiting additional 30 seconds for slower connections.")
    await tab.sleep(30)

    
    browser.stop()

    
    asyncio.get_event_loop().stop()

async def send_handler(event: cdp.network.RequestWillBeSent):
    if "/youtubei/v1/player" in event.request.url:
        post_data = event.request.post_data
        post_data_json = json.loads(post_data)
        
        if checkpotoken.get() == 1:
            potoken_textbox.insert("1.0", "po_token: " + post_data_json["serviceIntegrityDimensions"]["poToken"] + "\n")
        
        if checkvisitordata.get() == 1:
            visitordata_textbox.insert("1.0", "visitor_data: " + post_data_json["context"]["client"]["visitorData"] + "\n")
        
    return  

if __name__ == '__main__':
    def retrieving():
        checkpotoken.configure(state="disabled")
        checkvisitordata.configure(state="disabled")
        loop().run_until_complete(main())

    retrieve_button = ct.CTkButton(app, text="Retrieve keys", command=retrieving)
    retrieve_button.pack(padx=(10, 10), pady=(10, 10))

    checkpotoken = ct.CTkCheckBox(app, text="Retrieve po_token")
    checkpotoken.pack(padx=(10, 10), pady=(10, 10))

    checkvisitordata = ct.CTkCheckBox(app, text="Retrieve visitor_data")
    checkvisitordata.pack(padx=(10, 10), pady=(10, 10))

    
    potoken_textbox = ct.CTkTextbox(app, width=400, height=80, wrap="word")
    potoken_textbox.pack(padx=(10, 10), pady=(10, 10))

    visitordata_textbox = ct.CTkTextbox(app, width=400, height=80, wrap="word")
    visitordata_textbox.pack(padx=(10, 10), pady=(10, 10))

    app.mainloop()
