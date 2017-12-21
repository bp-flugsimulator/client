# Client für bp-flugsimulator

## Installieren

```sh
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
1. Den [bp-flugsimulator/server](https://github.com/bp-flugsimulator/server) starten, zuvor aber in das richtige Verzeichnis wechseln
    ```sh
    cd ../server
    python manage.py runserver 0.0.0.0:8000
    ```
1. Im Webbrowser `127.0.0.1:8000/slaves` aufrufen und den Client mit `172.18.0.2` hinzufügen. MAC-Adresse ist egal, da Docker das nicht kann.
1. Den Client mit Docker starten
    ```sh
    docker run --net slave_net --ip 172.18.0.2 bp-client 172.18.0.1 8000
    ```
1. Test Programm für den eben hinzugefügten Client hinzufügen mit dem Namen `Test` und dem Path `bash` und dem Argument `-c "echo $(date)"`.
1. Das Program ausführen.
1. In der Konsole mit dem Docker Image sollte zusehen sein, dass der Command angekommen ist
