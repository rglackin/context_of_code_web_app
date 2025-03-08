from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Column, Float, ForeignKey, Integer, Table, Text
from sqlalchemy.sql.sqltypes import NullType
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid

db = SQLAlchemy()

class Aggregator(db.Model):
    __tablename__ = 'aggregators'
    aggregator_id = db.Column(db.Integer, primary_key=True)
    guid = db.Column(db.Text, unique=True, nullable=False)
    name = db.Column(db.Text, nullable=False)

    devices = db.relationship('Device')
    
    def __repr__(self):
        return f'<Aggregator {self.name}>'
    
class Device(db.Model):
    __tablename__ = 'devices'
    device_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text(100), nullable=False)
    aggregator_id = db.Column(db.ForeignKey('aggregators.aggregator_id'), nullable=False)
    
    aggregator = db.relationship('Aggregator')
    snapshots = db.relationship('Snapshot')
    metric_types = db.relationship('DeviceMetricType')

    def __repr__(self):
        return f'<Device {self.name}>'

class Snapshot(db.Model):
    __tablename__ = 'snapshots'
    snapshot_id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.ForeignKey('devices.device_id'), nullable=False)
    client_timestamp_epoch = db.Column(db.Integer, nullable=False)
    client_timezon_mins = db.Column(db.Integer, nullable=False)
    server_timestamp_epoch = db.Column(db.Integer, nullable=False)
    server_timezone_mins = db.Column(db.Integer, nullable=False)
    
    device = db.relationship('Device')
    metrics = db.relationship('Metric')

    def __repr__(self):
        return f'<Snapshot {self.device_id}>'
    
class DeviceMetricType(db.Model):
    __tablename__ = 'device_metric_types'
    device_metric_type_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text(100), nullable=False)
    device_id = db.Column(db.ForeignKey('devices.device_id'), nullable=False)
    
    device = db.relationship('Device')
    metrics = db.relationship('Metric')

    def __repr__(self):
        return f'<DeviceMetricType {self.name}>'

class Metric(db.Model):
    __tablename__ = 'metrics'
    metric_id = db.Column(db.Integer, primary_key=True)
    snapshot_id = db.Column(db.ForeignKey('snapshots.snapshot_id'), nullable=False)
    value = db.Column(db.Float, nullable=False)
    device_metric_type_id = db.Column(db.ForeignKey('device_metric_types.device_metric_type_id'), nullable=False)
    
    snapshot = db.relationship('Snapshot')
    device_metric_type = db.relationship('DeviceMetricType')
    
    def __repr__(self):
        return f'<Metric {self.device_metric_type.name}:{self.value}>'