import json
import logging
import random
from typing import Any

import boto3

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


def vary_telemetry_value(value: Any) -> Any:
    """Randomly increases or decreases float telemetry values, except binary states."""
    if isinstance(value, float) and value not in (0.0, 1.0):
        delta = round(random.uniform(0.1, 1.0), 1)
        direction = random.choice([-1, 1])
        return round(value + (delta * direction), 1)

    return value


def build_telemetry_payload(thing_name: str, telemetry: dict) -> dict:
    """Builds a publishable telemetry payload from caller-provided metrics."""
    return {
        "device_id": thing_name,
        **{label: vary_telemetry_value(value) for label, value in telemetry.items()},
    }


def publish_device_telemetry(thing_name: str, telemetry: dict) -> None:
    """Sends caller-provided telemetry metrics to the device telemetry stream."""
    telemetry_topic = f"devices/{thing_name}/telemetry"
    payload = build_telemetry_payload(thing_name, telemetry)
    
    try:
        logger.info(f"[{thing_name}] Publishing sensor telemetry to stream: {telemetry_topic}")
        iot_client.publish(topic=telemetry_topic, qos=0, payload=json.dumps(payload))
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
        telemetry = event.get('telemetry')
        if not isinstance(telemetry, dict):
            logger.error("Missing or invalid required parameter: telemetry")
            return {'statusCode': 400, 'body': json.dumps('Error: missing or invalid telemetry')}

        logger.info(f"[{thing_name}] Invoked by EventBridge. Executing Cron Telemetry Stream.")
        publish_device_telemetry(thing_name, telemetry)
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
