from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()

from .config import DevelopmentConfig, TestingConfig
from .extensions import db, migrate, cache, limiter


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
    limiter.init_app(app)

    # Import models
    from .models import User, Recipe

    # Import blueprints
    from .routes.auth import auth_bp
    from .routes.recipes import recipes_bp

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp)

    # Rate limit error handler
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            "error": "rate limit exceeded",
            "message": str(error.description),
        }), 429

    return app


def create_test_app():
    return create_app(TestingConfig)