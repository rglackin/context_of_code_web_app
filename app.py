from flask import Flask
from models import db
from routes import bp as main_bp
from my_logging.logger import setup_logging
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

app.register_blueprint(main_bp)

if __name__ == '__main__':
    setup_logging()
    with app.app_context():
        db.create_all()
        logging.info("Database Setup Successfully")
        
    app.run(debug=True)
    logging.info("Application Completed Successfully") 
