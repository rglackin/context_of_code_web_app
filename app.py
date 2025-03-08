from flask import Flask
from models import db
from routes import bp as main_bp
from my_logging.logger import setup_logging # type: ignore
import logging
import json
import os 

app = Flask(__name__)
with open('config.json') as config_file:
    config = json.load(config_file)


app.config['SQLALCHEMY_DATABASE_URI'] = config['database']['connection_string']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
setup_logging()

app.logger.handlers = logging.getLogger().handlers
app.logger.setLevel(logging.DEBUG)
app.register_blueprint(main_bp)

app.logger.info("App Setup Successfully")

if __name__ == '__main__':
    
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        app.logger.info(f"Tables: {tables}")
        
        db.create_all()
        app.logger.info("Database Setup Successfully")
        
    app.run()
