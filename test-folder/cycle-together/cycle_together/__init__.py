from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_mail import Mail

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
mail = Mail()

def create_app():
    app = Flask(__name__)
    
    app.config["SECRET_KEY"] = "cycle-together-secret-key-2025"
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://26_webapp_50:5uJO74N6@mysql.lab.it.uc3m.es/26_webapp_50a?charset=utf8mb4"
    
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    
    db.init_app(app)
    mail.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    from . import model
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(model.User, int(user_id))
    
    from . import auth, main, trips
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(trips.bp)
    
    return app