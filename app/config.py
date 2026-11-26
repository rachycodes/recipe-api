
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_TYPE = "SimpleCache"
CACHE_DEFAULT_TIMEOUT = 60
class Config:
    """Shared application settings."""

    DATABASE = str(BASE_DIR / "recipes.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    CACHE_TYPE = "SimpleCache"
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_DEFAULT = "5 per minute"
    RATELIMIT_HEADERS_ENABLED = True

class ProductionConfig(Config):
    DATABASE = str(BASE_DIR / "recipes.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE}"


class TestingConfig(DevelopmentConfig):
    TESTING = True
    DEBUG = False
    DATABASE = str(BASE_DIR / "recipes_test.db")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE}"
    RATELIMIT_ENABLED = False