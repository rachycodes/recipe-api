class Config:
    """Shared settings. DATABASE is the dev default for now."""
    DATABASE = "recipes_alt.db"


class DevelopmentConfig(Config):
    pass


class ProductionConfig(Config):
    DATABASE = "recipes.db"