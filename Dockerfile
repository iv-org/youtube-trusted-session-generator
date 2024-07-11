FROM python:3.12-alpine
 
RUN apk add --no-cache \
      chromium \
      nss \
      freetype \
      freetype-dev \
      harfbuzz \
      ca-certificates \
      ttf-freefont

WORKDIR /usr/app/src
COPY index.py requirements.txt ./

RUN pip install -r requirements.txt
 
# Run
CMD [ "python", "./index.py"]