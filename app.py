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


with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        app.logger.debug(f"Tables before creation: {tables}")
        
        db.create_all()
        
        app.logger.debug(f"Tables after creation: {tables}")
        
        app.logger.info("Database Setup Successfully")

app.register_blueprint(main_bp)

app.logger.info("App Setup Successfully")

def clear_all_data():
    with app.app_context():
        # Get all tables/models
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            app.logger.info(f"Clearing table {table}")
            db.session.execute(table.delete())
        db.session.commit()
        app.logger.info("All data cleared from database")

@app.cli.command("clear-db")
def clear_db_command():
    """Clear all data from the database."""
    clear_all_data()
    print("Database cleared!")
    
if __name__ == '__main__':
    app.run()
