'''Initialize app extensions'''

import flask_sqlalchemy
import flask_apscheduler
import prometheus_flask_exporter

db = flask_sqlalchemy.SQLAlchemy()
scheduler = flask_apscheduler.APScheduler()


def init_exporter(app):
    exporter = prometheus_flask_exporter.PrometheusMetrics(app)
    exporter.info('app_info', 'OracleDB Exporter', version='0.1.6')
    return exporter
