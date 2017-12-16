FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt /src/requirements.txt
RUN pip install --no-cache-dir -r /src/requirements.txt

COPY . /usr/src/app
RUN python /usr/src/app/setup.py install

# websockets
EXPOSE 8000

ENTRYPOINT bp-flugsimulator-client

CMD ["--help"]
