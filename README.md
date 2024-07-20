# YouTube trusted session generator

## Description

This script will output two parameters: po_token and visitor_data. Needed for passing YouTube checks in Invidious.

## Tutorial without Docker
1. Install Chromium or Google Chrome.
2. Create a new virtualenv: `virtualenv venv`
3. Activate the virtualenv: `source venv/bin/activate`
4. Install the dependencies: `pip install -r requirements.txt`
5. Run the script: `python index.py`
6. Copy paste the values of these the two parameters (po_token and visitor_data) in config.yaml
   ```
   po_token: XXX
   visitor_data: XXX
   ```
7. Restart Invidious.

## Tutorial with Docker
1. Run the script: `docker run quay.io/invidious/youtube-trusted-session-generator`
2. Copy paste the values of these the two parameters (po_token and visitor_data) in config.yaml
   ```
   po_token: XXX
   visitor_data: XXX
   ```
3. Restart Invidious.
