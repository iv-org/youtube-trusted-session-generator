FROM python:3.12-alpine

# Install dependencies
RUN apk add --no-cache \
      xvfb \
      x11vnc \
      fluxbox \
      nss \
      freetype \
      freetype-dev \
      harfbuzz \
      ca-certificates \
      ttf-freefont \
      chromium \
      chromium-chromedriver

# Install x11vnc
RUN mkdir ~/.vnc
RUN x11vnc -storepasswd 1234 ~/.vnc/passwd

WORKDIR /usr/app/src
COPY index.py requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY docker/scripts/startup.sh ./
 
# Run
CMD [ "./startup.sh"]