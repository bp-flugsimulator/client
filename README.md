# Client fÃ¼r bp-flugsimulator

## Installieren

```
sudo pip install git+https://git@github.com/bp-flugsimulator/client.git#egg=bp-flugsimulator-client
```

## Docker

1. Docker installieren
1. ```docker build . -t bp-client -f bp-client.dockerfile``` Build Images
1. (Optional) ```docker image prune``` Löscht alle alten Images
1. ```docker run -t bp-client``` Führt den container aus
