from flask import Flask
from dotenv import load_dotenv

from .config import DevelopmentConfig
from .db import init_db, close_db

load_dotenv()


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    print("STARTING APP WITH DATABASE:", app.config["DATABASE"])

    # Import blueprints
    from .routes.auth import auth_bp
    from .routes.recipes import recipes_bp

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp)

    # Database cleanup
    app.teardown_appcontext(close_db)

    # Initialize database
    init_db(app.config["DATABASE"])

    return app