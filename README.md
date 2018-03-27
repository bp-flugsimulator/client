# Client für bp-flugsimulator

## Installation
1. Download and install python 3.4 or newer
1. Open cmd/terminal
1.  Create and navigate to the install directory (ATTENTION!!! spaces in this path can lead to unexpected behavior)
    ```sh
    md C:\fsim-client
    cd C:\fsim-client\
    ```
    or
    ```sh
    mkdir /home/fsim-user/fsim-client
    cd /home/fsim-user/fsim-client/
    ```
1. Download the Client in one of the following ways:
    1.  Clone the repository from github:  
        To use this option you need to install git first.
        ```sh
        git clone https://github.com/bp-flugsimulator/client
        ```
    1.  Download it from a running server instance from the local network:  
       To use this option the file install.py is needed from the repository.
       The example is given with a sever with the ip 0.0.0.0 on port 4242.
        ```sh
        python install.py --download-client 0.0.0.0:4242
        ```
1. Install the python dependencies with install.py (which comes with the client files):
    ```sh
    python install.py
    ```
    If the python installation is to old the script will fail on the first attempt.



## Docker Testing (internal)
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
