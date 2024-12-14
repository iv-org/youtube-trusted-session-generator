#!/bin/sh

echo "[INFO] internally launching GUI (X11 environment)"

XVFB_WHD=${XVFB_WHD:-1280x720x16}

echo "[INFO] starting Xvfb"
Xvfb :99 -ac -screen 0 $XVFB_WHD -nolisten tcp > /dev/null 2>&1 &
sleep 2

echo "[INFO] launching chromium instance"

if [ -z $HOST ]; then
	echo "[ERROR] Missing environment variable \$HOST."
	exit 1
fi

if [ -z $PORT ]; then
	echo "[ERROR] Missing environment variable \$PORT."
	exit 1
fi

# Run python script on display 0
DISPLAY=:99 python potoken-generator.py --bind $HOST --port $PORT
