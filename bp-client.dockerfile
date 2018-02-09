FROM alpine:latest

MAINTAINER "https://github.com/bp-flugsimulator"
ENV PYTHONUNBUFFERED 0
RUN apk add --no-cache python3 git python3-dev gcc musl-dev linux-headers

WORKDIR /usr/src/app

COPY linux_requirements.txt /src/requirements.txt
RUN pip3 install --no-cache-dir -r /src/requirements.txt

COPY . /usr/src/app
RUN python3 /usr/src/app/setup.py install

COPY applications/* /usr/bin/

# websockets
EXPOSE 8000

ENTRYPOINT ["bp-flugsimulator-client"]
