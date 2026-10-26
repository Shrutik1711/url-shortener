from flask import Flask 
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///links.db"
    if config :
        app.config.update(config)
    db.init_app(app)  
    from .routes import bp
    app.register_blueprint(bp)  
    with app.app_context():
        from . import models
        db.create_all()
    return app    