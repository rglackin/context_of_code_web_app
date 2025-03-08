from models import *
from datetime import timezone, datetime
import logging

logger = logging.getLogger(__name__)
#session = db.session
def map_dto_to_model(aggregator_dto, session):
    logger.info(f"Beginning Mapping DTO to Model")
    
    # Check if the aggregator already exists
    aggregator_model = session.query(Aggregator).filter_by(guid=aggregator_dto.guid).first()
    if not aggregator_model:
        logger.debug("Aggregator does not exist. Creating new aggregator")
        aggregator_model = Aggregator(
            guid=aggregator_dto.guid,
            name=aggregator_dto.name
        )
        session.add(aggregator_model)
        session.flush()
        logger.debug("Aggregator created")
    
    for device_dto in aggregator_dto.devices:
        # Check if the device already exists
        device_model = session.query(Device).filter_by(name=device_dto.name, aggregator=aggregator_model).first()
        if not device_model:
            device_model = Device(
                name=device_dto.name,
                aggregator=aggregator_model
            )
            session.add(device_model)
            session.flush()
        
        for snapshot_dto in device_dto.snapshots:
            snapshot_model = Snapshot(
                device=device_model,
                client_timestamp_epoch=int(snapshot_dto.timestamp_capture.timestamp()),
                client_timezon_mins=snapshot_dto.timezone_mins,
                server_timestamp_epoch=int(datetime.now(timezone.utc).timestamp()),
                server_timezone_mins=datetime.now(timezone.utc).utcoffset().total_seconds() // 60
            )
            
            for metric_dto in snapshot_dto.metrics:
                # Check if the metric type already exists
                metric_type_model = session.query(DeviceMetricType).filter_by(name=metric_dto.name, device=device_model).first()
                if not metric_type_model:
                    metric_type_model = DeviceMetricType(
                        name=metric_dto.name,
                        device=device_model
                    )
                    session.add(metric_type_model)
                    session.flush()
                metric_model = Metric(
                    snapshot=snapshot_model,
                    value=metric_dto.value,
                    device_metric_type=metric_type_model
                )
                
                session.add(metric_model)
                session.flush()
            session.add(snapshot_model)
            session.flush()
    session.commit()
    session.close()
    
    