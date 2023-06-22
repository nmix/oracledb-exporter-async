FROM python:3.11-slim-bullseye

RUN apt-get update \
    && apt-get install --no-install-recommends -y alien=8.95.4 libaio1=0.3.112-9 wget=1.21-1+deb11u1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q https://download.oracle.com/otn_software/linux/instantclient/oracle-instantclient-basic-linuxx64.rpm \
    && wget -q https://download.oracle.com/otn_software/linux/instantclient/oracle-instantclient-sqlplus-linuxx64.rpm \
    && wget -q https://download.oracle.com/otn_software/linux/instantclient/oracle-instantclient-devel-linuxx64.rpm

RUN alien -i  oracle-instantclient-basic-linuxx64.rpm \
    && alien -i  oracle-instantclient-sqlplus-linuxx64.rpm \
    && alien -i  oracle-instantclient-devel-linuxx64.rpm

RUN pip install --no-cache-dir poetry==1.4.1 waitress==2.1.2

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry export --output requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

COPY odbe odbe

COPY custom_metrics.toml custom_metrics.toml

EXPOSE 8080

ENTRYPOINT ["waitress-serve", "--call", "odbe:create_app"]
