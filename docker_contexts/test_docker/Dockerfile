FROM python:3.8.3-buster

RUN apt update && apt upgrade -y
RUN apt install -y \
    python3-pip \
    postgresql-client

WORKDIR /usr/local/test
COPY requirements.txt /usr/local/test/
RUN pip3 install -r requirements.txt
COPY . /usr/local/test/
ENTRYPOINT ["run_test.sh", "test.py"]
