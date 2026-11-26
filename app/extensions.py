from flask_sqlalchemy import SQLAlchemy
import sqlite3
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask_migrate import Migrate
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address



cache = Cache()
db = SQLAlchemy()
migrate = Migrate()
cache = Cache()



@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


limiter = Limiter(
    key_func=get_remote_address,
)