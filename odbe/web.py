import flask

import odbe

web_bp = flask.Blueprint('web_bp', __name__)


@web_bp.route('/')
def root():
    return f'OracleDB Exporter v{odbe.APP_VERSION}'
