from .extensions import db

class User(db.Model):
    __tablename__ = "users"
    recipes = db.relationship("Recipe", back_populates="user")
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    email = db.Column(db.String, nullable=False, unique=True)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False, server_default="user")

class Recipe(db.Model):
    __tablename__ = "recipes"
    user = db.relationship("User", back_populates="recipes")
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  
    title = db.Column(db.String, nullable=False)
    ingredients = db.Column(db.String, nullable=False)
    instructions = db.Column(db.String, nullable=False, server_default="")
    is_public = db.Column(db.Integer, nullable=False, server_default="1")
    category = db.Column(db.String(100), nullable=False, default="Uncategorized", server_default="Uncategorized")