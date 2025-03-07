from datetime import datetime
import logging.config
import json
import os

def setup_logging(
    default_path=None,
    default_level=logging.INFO,
    env_key='LOG_CFG'
):
    """Setup logging configuration"""
    if default_path is None:
        # Determine the path to the config.json file relative to this script
        default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        
        # Ensure the logs directory exists in the current working directory
        log_dir = os.path.join(os.getcwd(), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Set the filename dynamically based on the current date
        date_str = datetime.now().strftime('%Y-%m-%d')
        config['handlers']['file']['filename'] = os.path.join(log_dir, f'{date_str}.json')

        logging.config.dictConfig(config)
    else:
        print(f"Logging Configuration File Not Found: {path}")
        logging.basicConfig(level=default_level)

if __name__ == "__main__":
    setup_logging()