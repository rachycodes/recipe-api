
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Shared application settings."""

    DATABASE = str(BASE_DIR / "recipes_alt.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    pass


class ProductionConfig(Config):
    DATABASE = str(BASE_DIR / "recipes.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE}"


class TestingConfig(DevelopmentConfig):
    TESTING = True
    DEBUG = False
    DATABASE = str(BASE_DIR / "recipes_test.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE}"
