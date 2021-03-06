FROM python:3

MAINTAINER "https://github.com/bp-flugsimulator"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./setup.py", "test" ]
