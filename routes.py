from flask import Blueprint, jsonify, request
from models import *
from datetime import datetime
from dto_datamodel import DTO_Aggregator
from aggregator_mapping import map_dto_to_model
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dto_datamodel import *
import json
from reticker import TickerExtractor

# Create blueprint - note we no longer need url_prefix here as it's defined in app.py
bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

STOCK_SYMBOLS_CACHE = ["AAPL", "MSFT", "GOOG", "AMZN"]
# Root route for API
@bp.route('/')
def home():
    return jsonify({"message": "API is working - Dashboard is available at the root URL /"})

# Aggregator route - now at /api/aggregator because of the prefix in app.py
@bp.route('/aggregator', methods=['GET', 'POST'])
def handle_aggregator():
    if request.method == 'POST':
        return add_aggregator()
    elif request.method == 'GET':
        return get_aggregator()

def add_aggregator():
    try:
        session = db.session
        data = request.get_json()
        logger.info("Received data")
        if not data:
            logger.error("Invalid data received")
            return jsonify({"error": "Invalid data"}), 400
        
        logger.debug(data)
        # Deserialize JSON to DTO
        logger.info("Deserializing JSON to DTO")
        logger.debug(f"Data: {data}")
        aggregator_dto = DTO_Aggregator.from_json(data)
        logger.info("Deserialization complete")
        
        # Map DTO to models and save to the database
        logger.info("Mapping DTO to Model")
        map_dto_to_model(aggregator_dto, session)
        logger.info("Mapping complete")
        
        return jsonify({"message": "Aggregator added successfully"}), 201
    except Exception as e:
        logger.error(f"Error in add aggregator route: {e}")
        if session is not None:
            logger.error("Rolling back session")
            try:
                session.rollback()
                session.close()
            except Exception as e:
                logger.error(f"Error rolling back session: {e}")
            
        return jsonify({
                        "status": "error",
                        "message": str(e)
                        }), 500

def get_aggregator():
    try:
        session = db.session
        uuid = request.args.get('uuid')
        
        aggregators = []
        if uuid:
            logger.info(f"Fetching aggregator with UUID: {uuid}")
            # Fetch a single aggregator by UUID
            aggregators = session.query(Aggregator).filter_by(guid=uuid)
            logger.info("Aggregator fetched")
            if not aggregators:
                return jsonify({"error": "Aggregator not found"}), 404
        else:
            # Fetch all aggregators
            logger.info("Fetching all aggregators")
            aggregators = session.query(Aggregator).all()
        aggregators_dto = [
            DTO_Aggregator(
                guid=aggregator.guid,
                name=aggregator.name,
                devices=[
                    DTO_Device(
                        name=device.name,
                        snapshots=[
                            DTO_Snapshot(
                                timestamp_capture=datetime.fromtimestamp(snapshot.client_timestamp_epoch),
                                timezone_mins=snapshot.client_timezon_mins,
                                metrics=[
                                    DTO_Metric(
                                        name=metric.device_metric_type.name,
                                        value=metric.value
                                    ) for metric in snapshot.metrics
                                ]
                            ) for snapshot in device.snapshots
                        ]
                    ) for device in aggregator.devices
                ]
            ).to_dict() for aggregator in aggregators
        ]
        logger.info("Aggregators fetched")
        return jsonify(aggregators_dto), 200
    except Exception as e:
        logger.error(f"Error in get aggregator route: {e}")
        return jsonify({
                        "status": "error",
                        "message": str(e)
                        }), 500

@bp.route('/stock-symbols', methods=['GET'])
def handle_stock_symbols():
    if request.method == 'GET':
        return get_stock_symbols()

def add_stock_symbols():
    try:
        global STOCK_SYMBOLS_CACHE
        logger.info("Received stock symbols")
        data = request.get_json()
        logger.debug(f"Data received: {data}")
        if not data or 'symbols' not in data:
            return jsonify({"error": "No symbols provided"}), 400
        
        # Convert to uppercase and remove duplicates
        input_symbols = [symbol.upper().strip() for symbol in data['symbols']]
        input_symbols = list(set(input_symbols))  # Remove duplicates
        
        # Validate the symbols using reticker
        extractor = TickerExtractor()
        valid_symbols = []
        invalid_symbols = []
        
        for symbol in input_symbols:
            # Check if symbol is valid
            extracted = extractor.extract(symbol)
            if extracted and symbol in extracted:
                valid_symbols.append(symbol)
            else:
                invalid_symbols.append(symbol)
        
        logger.info(f"Valid symbols: {valid_symbols}")
        if invalid_symbols:
            logger.warning(f"Invalid symbols: {invalid_symbols}")
        
        if not valid_symbols:
            return jsonify({
                "error": "No valid stock symbols provided",
                "invalid_symbols": invalid_symbols
            }), 400
        
        # Replace the cache with the new symbols
        STOCK_SYMBOLS_CACHE = valid_symbols
        
        logger.info(f"Updated stock symbol cache: {STOCK_SYMBOLS_CACHE}")
        
        response_data = {
            "message": f"{len(valid_symbols)} valid symbols received",
            "symbols": valid_symbols,
            "all_symbols": STOCK_SYMBOLS_CACHE
        }
        
        if invalid_symbols:
            response_data["warning"] = f"{len(invalid_symbols)} invalid symbols were ignored"
            response_data["invalid_symbols"] = invalid_symbols
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error processing stock symbols: {e}")
        return jsonify({"error": str(e)}), 500

def get_stock_symbols():
    try:
        # Return the symbols from our cache
        global STOCK_SYMBOLS_CACHE
        logger.info(f"Returning stock symbols from cache: {STOCK_SYMBOLS_CACHE}")
        return jsonify({"symbols": STOCK_SYMBOLS_CACHE}), 200
    except Exception as e:
        logger.error(f"Error retrieving stock symbols: {e}")
        return jsonify({"error": str(e)}), 500
    
# Add this new function for internal calls from Dash
def add_stock_symbols_internal(data):
    try:
        global STOCK_SYMBOLS_CACHE
        logger.info("Processing stock symbols internally")
        
        if not data or 'symbols' not in data:
            return {"error": "No symbols provided"}, 400
        
        # Convert to uppercase and remove duplicates
        input_symbols = [symbol.upper().strip() for symbol in data['symbols']]
        input_symbols = list(set(input_symbols))  # Remove duplicates
        
        # Validate the symbols using reticker
        extractor = TickerExtractor()
        valid_symbols = []
        invalid_symbols = []
        
        for symbol in input_symbols:
            # Check if symbol is valid
            extracted = extractor.extract(symbol)
            if extracted and symbol in extracted:
                valid_symbols.append(symbol)
            else:
                invalid_symbols.append(symbol)
        
        logger.info(f"Valid symbols: {valid_symbols}")
        if invalid_symbols:
            logger.warning(f"Invalid symbols: {invalid_symbols}")
        
        if not valid_symbols:
            return {
                "error": "No valid stock symbols provided",
                "invalid_symbols": invalid_symbols
            }, 400
        
        # Replace the cache with the new symbols
        STOCK_SYMBOLS_CACHE = valid_symbols
        
        logger.info(f"Updated stock symbol cache: {STOCK_SYMBOLS_CACHE}")
        
        response_data = {
            "message": f"{len(valid_symbols)} valid symbols received",
            "symbols": valid_symbols,
            "all_symbols": STOCK_SYMBOLS_CACHE
        }
        
        if invalid_symbols:
            response_data["warning"] = f"{len(invalid_symbols)} invalid symbols were ignored"
            response_data["invalid_symbols"] = invalid_symbols
        
        return response_data, 200
        
    except Exception as e:
        logger.error(f"Error processing stock symbols internally: {e}")
        return {"error": str(e)}, 500