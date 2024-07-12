import os

from flask import Flask
from flask_mail import Mail

from src.datastore import db
from src.config import config


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "development")

    # instantiate the app
    app = Flask(__name__)

    # set config
    config_env = config[config_name]
    app.config.from_object(config_env)

    # set up extensions
    Mail(app)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    # shell context for flask cli
    @app.shell_context_processor
    def ctx():
        return {"app": app, "db": db}

    return app


