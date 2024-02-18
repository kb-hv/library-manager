from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from os import environ

db = SQLAlchemy()

def create_app():
  app = Flask(__name__)
  app.config['SECRET_KEY'] = environ.get('SECRET_KEY')
  app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
  db.init_app(app)
  
  from .auth import auth
  from .views_member import views_member
  from .views_book import views_book
  
  app.register_blueprint(views_member, url_prefix='/')
  app.register_blueprint(views_book, url_prefix='/')
  app.register_blueprint(auth, url_prefix='/')
  
  from .models import User, Book, Member, Transaction
  
  with app.app_context():
    # Member.__table__.drop(db.engine)
    # Transaction.__table__.drop(db.engine)
    # Book.__table__.drop(db.engine)
    db.create_all()
  
  login_manager = LoginManager()
  login_manager.login_view = 'auth.login'
  login_manager.init_app(app)
  
  @login_manager.user_loader
  def load_user(id):
    return User.query.get(int(id))
  
  return app
