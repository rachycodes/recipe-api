from flask import Flask
from dotenv import load_dotenv
from .config import DevelopmentConfig, TestingConfig
from .extensions import db, migrate, cache

load_dotenv()


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    print(
        "STARTING APP WITH DATABASE:",
        app.config["SQLALCHEMY_DATABASE_URI"]
    )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)

    # Import the models
    from .models import User, Recipe

    # Import the blueprints
    from .routes.auth import auth_bp
    from .routes.recipes import recipes_bp

    # Register the blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp)

    return app


def create_test_app():
    return create_app(TestingConfig)