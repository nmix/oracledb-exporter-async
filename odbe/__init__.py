'''Application factory setup'''

import os
import flask

from odbe import extensions as ext
from odbe import web
from odbe import tasks

APP_VERSION = '0.1.6'

DATA_SOURCE_NAME = os.environ.get(
        'DATA_SOURCE_NAME',
        'oracle+oracledb://system:oracle@localhost:1521/xe'
        )

CUSTOM_METRICS = os.environ.get('CUSTOM_METRICS', './custom_metrics.toml')


def create_app(test_config=None):
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
            SECRET_KEY='dev',
            SQLALCHEMY_DATABASE_URI=DATA_SOURCE_NAME,
            SQLALCHEMY_ENGINE_OPTIONS={'thick_mode': True},
            CUSTOM_METRICS=CUSTOM_METRICS,
            LOG_LEVEL=os.environ.get("LOG_LEVEL", "INFO"),
            MISFIRE_GRACE_TIME=int(os.environ.get('MISFIRE_GRACE_TIME', '60')),
            )
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    app.logger.propagate = False
    app.logger.setLevel(app.config["LOG_LEVEL"])

    ext.db.init_app(app)
    ext.scheduler.init_app(app)
    ext.init_exporter(app)

    with app.app_context():
        app.register_blueprint(web.web_bp)
        ext.scheduler.start()
        tasks.load(CUSTOM_METRICS)

    return app
