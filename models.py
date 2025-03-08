from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Column, Float, ForeignKey, Integer, Table, Text
from sqlalchemy.sql.sqltypes import NullType
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()
metadata = Base.metadata
db = SQLAlchemy()

class Aggregator(Base):
    __tablename__ = 'aggregators'
    aggregator_id = Column(Integer, primary_key=True)
    guid = Column(Text(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    name = Column(Text(100), nullable=False)

    def __repr__(self):
        return f'<Aggregator {self.name}>'
    
class Device(Base):
    __tablename__ = 'devices'
    device_id = Column(Integer, primary_key=True)
    name = Column(Text(100), nullable=False)
    aggregator_id = Column(ForeignKey('aggregators.aggregator_id'), nullable=False)
    
    aggregator = relationship('Aggregator')

    def __repr__(self):
        return f'<Device {self.name}>'

class Snapshot(Base):
    __tablename__ = 'snapshots'
    snapshot_id = Column(Integer, primary_key=True)
    device_id = Column(ForeignKey('devices.device_id'), nullable=False)
    client_timestamp_epoch = Column(Integer, nullable=False)
    client_timezon_mins = Column(Integer, nullable=False)
    server_timestamp = Column(Integer, nullable=False)
    server_timezone_mins = Column(Integer, nullable=False)
    
    device = relationship('Device')

    def __repr__(self):
        return f'<Snapshot {self.device_id}>'
    
class DeviceMetricType(Base):
    __tablename__ = 'device_metric_types'
    device_metric_type_id = Column(Integer, primary_key=True)
    name = Column(Text(100), nullable=False)
    device_id = Column(ForeignKey('devices.device_id'), nullable=False)
    
    device = relationship('Device')

    def __repr__(self):
        return f'<DeviceMetricType {self.name}>' 

class Metric(Base):
    __tablename__ = 'metrics'
    metric_id = Column(Integer, primary_key=True)
    snapshot_id = Column(ForeignKey('snapshots.snapshot_id'), nullable=False)
    value = Column(Float, nullable=False)
    device_metric_type_id = Column(ForeignKey('device_metric_types.device_metric_type_id'), nullable=False)
    
    snapshot = relationship('Snapshot')
    device_metric_type = relationship('DeviceMetricType')
    
    def __repr__(self):
        return f'<Metric {self.device_metric_type.name}:{self.value}>'