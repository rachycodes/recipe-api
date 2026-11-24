# from app import create_app
# from app.config import ProductionConfig

# app = create_app(ProductionConfig)


from app import create_app
from app.config import DevelopmentConfig

app = create_app(DevelopmentConfig)