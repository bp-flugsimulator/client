# Client für bp-flugsimulator

## Installieren

```
sudo pip install git+https://git@github.com/bp-flugsimulator/client.git#egg=bp-flugsimulator-client
```

## Docker Testing

1. Docker installieren
1. Repository clonen
    ```sh
    git clone https://github.com/bp-flugsimulator/client
    git clone https://github.com/bp-flugsimulator/server
    ```
1. In das Verzeichnis client wechseln
    ```sh
    cd client
    ```
1. Das Docker Image bauen, muss bei jedem update der Repository neu ausgeführt werden
    ```sh
    docker build . -t bp-client -f bp-client.dockerfile
    ```
1. Das Docker Netzwerk erstellen, damit client und server sich verbinden können, muss nur einmalig ausgeführt werden
    ```sh
    docker network create --subnet=172.18.0.0/16 slave_net
    ```
1. In der [bp-flugsimulator/server](https://github.com/bp-flugsimulator/server) Repository in der Datei `server/settings.py` den Folgenden Parameter setzten
    ```py
    ALLOWED_HOSTS=["172.18.0.0", "localhost", "127.0.0.1"]
    ```
1. [bp-flugsimulator/server](https://github.com/bp-flugsimulator/server) starten mit `python manage.py runserver 0.0.0.0:8000`
1. Den Client mit Docker starten
    ```sh
    docker run --net slave_net --ip 172.18.0.2 bp-client 172.18.0.1 8000
    ```
