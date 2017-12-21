# Client für bp-flugsimulator

## Installieren

```
sudo pip install git+https://git@github.com/bp-flugsimulator/client.git#egg=bp-flugsimulator-client
```

## Docker Testing

1. Docker installieren
1. Repository clonen
1. In das geclonte Verzeichnis wechseln
1. ```docker build . -t bp-client -f bp-client.dockerfile``` Build Images
1. ```docker network create --subnet=172.18.0.0/16 slave_net```
1. In `server/settings.py` `ALLOWED_HOSTS=["172.18.0.0", "localhost", "127.0.0.1"]` setzten
1. Server starten mit `python manage.py runserver 0.0.0.0:8000`
1. ```docker run --net slave_net --ip 172.18.0 bp-client [HOST] [PORT]``` Führt den container aus
