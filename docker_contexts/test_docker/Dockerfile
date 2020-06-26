FROM python:3.8.3-buster

RUN apt update && apt upgrade -y
RUN apt install python3-pip -y

WORKDIR /usr/local/test
COPY . /usr/local/test/
RUN pip3 install -r requirements.txt
ENTRYPOINT ["python3", "test.py"]
