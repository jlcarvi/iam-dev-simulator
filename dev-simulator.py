import json
import logging
import random
import boto3
from botocore.exceptions import ClientError

# SETUP LOGGING
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# GLOBAL INITIALIZATION
iot_client = boto3.client('iot-data')


def simulate_hardware_logic(thing_name: str, delta_state: dict) -> dict:
    """Accepts the cloud delta changes and treats them as the new hardware reality."""
    logger.info(f"[{thing_name}] Processing hardware changes: {delta_state}")
    return delta_state


def publish_shadow_update(thing_name: str, reported_state: dict) -> None:
    """Syncs the device status back to the IoT Core Device Shadow system."""
    target_topic = f"$aws/things/{thing_name}/shadow/update"
    payload = {"state": {"reported": reported_state}}
    
    try:
        logger.info(f"[{thing_name}] Publishing reported state to shadow: {target_topic}")
        iot_client.publish(topic=target_topic, qos=1, payload=json.dumps(payload))
        logger.info(f"[{thing_name}] Successfully updated shadow state.")
    except Exception as e:
        logger.error(f"[{thing_name}] Error during shadow publish: {str(e)}")
        raise e


def publish_device_telemetry(thing_name: str) -> None:
    """Generates fake sensor metrics and sends them to a telemetry data stream."""
    telemetry_topic = f"devices/{thing_name}/telemetry"
    
    fake_payload = {
        "device_id": thing_name,
        "room_temperature": round(random.uniform(-10.0, 15.5), 1),
        "exterior_temperature": round(random.uniform(10.0, 45.0), 1)
        #"battery_health": "good",
        #"signal_strength_dbm": random.randint(-85, -50)
    }
    
    try:
        logger.info(f"[{thing_name}] Publishing sensor telemetry to stream: {telemetry_topic}")
        iot_client.publish(topic=telemetry_topic, qos=0, payload=json.dumps(fake_payload))
        logger.info(f"[{thing_name}] Telemetry broadcast complete.")
    except Exception as e:
        logger.error(f"[{thing_name}] Telemetry error: {str(e)}")


def lambda_handler(event, context):
    logger.info(f"Received invocation event: {json.dumps(event)}")
    
    # 1. Always extract the thing_name first
    thing_name = event.get('thing_name')
    if not thing_name:
        logger.error("Missing required parameter: thing_name")
        return {'statusCode': 400, 'body': json.dumps('Error: missing thing_name')}

    # 2. ROUTING LOGIC: Determine who called the Lambda
    delta_state = event.get('state', {})
    
    # CASE A: Triggered by EventBridge (Only thing_name was passed, no 'state' block)
    if not delta_state:
        logger.info(f"[{thing_name}] Invoked by EventBridge. Executing Cron Telemetry Stream.")
        publish_device_telemetry(thing_name)
        return {
            'statusCode': 200,
            'body': json.dumps({'mode': 'telemetry_only', 'device': thing_name})
        }
        
    # CASE B: Triggered by IoT Rule (Contains a delta 'state' block)
    try:
        logger.info(f"[{thing_name}] Invoked by IoT Rule. Executing State Delta Sync.")
        new_reported_status = simulate_hardware_logic(thing_name, delta_state)
        publish_shadow_update(thing_name, new_reported_status)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'mode': 'shadow_sync',
                'device': thing_name,
                'state_synced': new_reported_status
            })
        }
        
    except Exception as error:
        logger.critical(f"[{thing_name}] Lambda execution failed: {str(error)}")
        return {'statusCode': 500, 'body': json.dumps('Internal simulator failure.')}
