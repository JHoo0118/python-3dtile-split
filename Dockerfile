FROM python:3.10.14-slim

WORKDIR /usr/proj/python-3dtile/

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libssl-dev libffi-dev libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /usr/proj/python-3dtile/
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache/pip

COPY ./app/ /usr/proj/python-3dtile/app/

ENTRYPOINT ["python", "app/main.py"]
