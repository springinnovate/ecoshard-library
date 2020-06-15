FROM python:3.7-alpine

ENV FLASK_APP test_flask.py
ENV FLASK_RUN_HOST 0.0.0.0

COPY . .
RUN pip install -r requirements.txt
CMD ["flask", "run"]
