#!/bin/sh

echo "[INFO] internally launching GUI (X11 environment)"

rm -f /tmp/.X0-lock

# Run Xvfb on display 0.
Xvfb :0 -screen 0 1280x720x16 &>/dev/null &

# Run fluxbox windows manager on display 0.
fluxbox -display :0 &>/dev/null &

# Run x11vnc on display 0
x11vnc -display :0 -forever -usepw &>/dev/null &

# Add delay
sleep 5

echo "[INFO] launching the python script"

# Run python script on display 0
DISPLAY=:0 python index.py
