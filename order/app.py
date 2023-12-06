import json
import boto3
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

TABLE_NAME = "orders"
SERVICE_NAME = 'iatk_demo.order_service'
EVENT_TYPE = 'order_created'

eventbridge = boto3.client('events')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    body = json.loads(event['body'])
    item = {
        'order_id': body['order_id'],
        'amount': body['amount'],
        'order_status': 'created'
    }
    dynamodb.Table(TABLE_NAME).put_item(Item=item)
    
    event_payload = {
        'EventBusName': 'default',
        'Source': SERVICE_NAME,
        'DetailType': EVENT_TYPE,
        'Detail': json.dumps(item)
    }
    eventbridge.put_events(
        Entries=[event_payload]
    )

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'order created'
        })
    }
