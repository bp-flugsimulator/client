# Client für bp-flugsimulator

## Installieren

```
sudo pip install git+https://git@github.com/bp-flugsimulator/client.git#egg=bp-flugsimulator-client
```

## Docker

1. Docker installieren
1. ```docker build . -t bp-client -f bp-client.dockerfile``` Build Images
1. (Optional) ```docker image prune``` L�scht alle alten Images
1. ```docker run -t bp-client``` F�hrt den container aus
