# Oracle DB Exporter (another one)

The project is inspired by the [iamseth/oracledb_exporter](https://github.com/iamseth/oracledb_exporter) with the addition of asynchronous requests.

Maybe, the main issue with the [iamseth/oracledb_exporter](https://github.com/iamseth/oracledb_exporter) is that the database queries are executed at the moment of collecting metrics from the exporter. These queries can be resource-intensive and we want to avoid slowing down Prometheus. This implementation is intended to be compatible with the original project, but there are several key differences:

* there are no default oracledb metrics;
* `DATA_SOURCE_NAME` has static format - `oracle+oracledb://system:oracle@localhost:1521/xe`;
* default port changed to 8080;

Technically it just [flask](https://flask.palletsprojects.com/en/2.2.x/) app with [APScheduler](https://pypi.org/project/APScheduler/) and [prometheus_client](https://pypi.org/project/prometheus-client/) packages.

## Asynchrony

In this project, the database query and Prometheus scraping are decoupled. The schedule or frequency of executing the database queries is determined by new fields `interval` and `cron` in the `[[metric]]` section of the *custom_metrics.toml* file (or any other TOML file specified by the `CUSTOM_METRICS` environment variable). 

The `interval` field specifies the execution interval of the query in seconds. For example, `interval = 30` means the query will be executed once every 30 seconds. The `cron` field defines the schedule for query execution in cron format. For instance, `cron = "*/5 * * * *"` means the query will be executed every 5 minutes.

Each `[[metric]]` section can have only one field defined - either `interval` or `cron`. If neither `interval` nor `cron` is specified, the default value of `interval = 30` will be set.

See *./custom_metrics.toml* in root project directory.

## Quickstart

```bash
# --- run oracledb container
docker run --rm --name oracle \
  -p 1521:1521 \
  wnameless/oracle-xe-11g-r2:18.04-apex

# --- run oracledb exporter
docker run --rm --name odbe \
  --network host \
  -p 8080:8080 \
  -e DATA_SOURCE_NAME=oracle+oracledb://system:oracle@localhost:1521/xe \
  zoidenberg/oracledb-exporter-async:latest


curl localhost:8080/metrics
# ...
# HELP context_with_interval_value_1 Simple example returning always 1.
# TYPE context_with_interval_value_1 gauge
context_with_interval_value_1 1.0
# HELP context_with_interval_value_2 Same but returning always 2.
# TYPE context_with_interval_value_2 gauge
context_with_interval_value_2 2.0
# HELP context_with_cron_value_1_total Simple example returning always 1.
# TYPE context_with_cron_value_1_total counter
context_with_cron_value_1_total{label_1="First label",label_2="Second label"} 1.0
# HELP context_with_cron_value_1_created Simple example returning always 1.
# TYPE context_with_cron_value_1_created gauge
context_with_cron_value_1_created{label_1="First label",label_2="Second label"} 1.686231900003406e+09
# HELP context_with_cron_value_2 Same but returning always 2.
# TYPE context_with_cron_value_2 gauge
context_with_cron_value_2{label_1="First label",label_2="Second label"} 2.0
```

Run exporter with external TOML file

```bash
docker run --rm --name odbe \
  --network host \
  -v /path/to/metrics.toml:/opt/metrics.toml \
  -p 8080:8080 \
  -e DATA_SOURCE_NAME=oracle+oracledb://system:oracle@localhost:1521/xe \
  -e CUSTOM_METRICS=/opt/metrics.toml \
  zoidenberg/oracledb-exporter-async:latest
```

## Development

### Requirements

* Python 3.11
* Poetry (https://python-poetry.org/)
* Oracle Instant Client (https://www.oracle.com/au/database/technologies/instant-client.html)

Oracle Instant Client for Ubuntu

Install client for "thick" mode, see https://python-oracledb.readthedocs.io/en/latest/user_guide/initialization.html#enabling-python-oracledb-thick-mode

```bash
wget https://download.oracle.com/otn_software/linux/instantclient/oracle-instantclient-basic-linuxx64.rpm
wget https://download.oracle.com/otn_software/linux/instantclient/oracle-instantclient-sqlplus-linuxx64.rpm
wget https://download.oracle.com/otn_software/linux/instantclient/oracle-instantclient-devel-linuxx64.rpm

sudo apt update
sudo apt install alien libaio1

sudo alien -i  oracle-instantclient-basic-linuxx64.rpm
sudo alien -i  oracle-instantclient-sqlplus-linuxx64.rpm
sudo alien -i  oracle-instantclient-devel-linuxx64.rpm
```


### Run on localhost

```bash
git clone https://github.com/nmix/oracledb-exporter-async.git
cd oracledb-exporter-async
poetry install --with dev
poetry shell
DEBUG_METRICS=1 flask --app odbe run --debug

# --- another terminal
http :5000
http :5000/metrics
```

### Connect to Oracle DB

Run Oracle DB container

```bash
docker run --name oracle -p 1521:1521 wnameless/oracle-xe-11g-r2:18.04-apex
```

Connect with oracledb library

```python
import oracledb

oracledb.init_oracle_client()

cp = oracledb.ConnectParams(user='system', password='oracle', host='localhost', port=1521, service_name='xe')
oracledb.connect(params=cp)
cursor = oracledb.connect(params=cp).cursor()
# --- or
cursor = oracledb.connect(user='system', password='oracle', dsn='localhost:1521/xe').cursor()
# --- or
cursor = oracledb.connect(dsn='system/oracle@localhost:1521/xe').cursor()
# ---
print([r for r in cursor.execute('select sysdate from dual')])
#=> [(datetime.datetime(2023, 5, 10, 13, 14, 13),)]
```

Connect with SQLAlchemy library

```python
import sqlalchemy as sa

engine = sa.create_engine('oracle+oracledb://system:oracle@localhost:1521/xe', thick_mode=True)
connection = engine.connect()
res = connection.execute(sa.text('select sysdate from dual')).fetchall()
print(res)
#=> [(datetime.datetime(2023, 5, 11, 7, 22, 30),)]

res = connection.execute(sa.text("SELECT 1 as value_1, 'First label' as label_1, 2 as value_2 FROM DUAL")).mappings().first()
print(res)
#=> {'value_1': 1, 'label_1': 'First label', 'value_2': 2}
```

### Dockerize

```bash
# --- build image
docker build . -t oracledb-exporter-async
# --- run container
docker run --rm --name odbe \
  -p 8080:8080 \
  -e DATA_SOURCE_NAME=oracle+oracledb://system:oracle@<SERVER_HOST>:1521/xe \
  oracledb_exporter
```

### Test

```bash
poetry install -with dev
poetry shell
pytest
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
