import json
import boto3
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

TABLE_NAME = "orders"

dynamodb = boto3.resource("dynamodb")

def lambda_handler(event, context):
    if event["detail"]["order_status"] != "created":
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "order status is invalid"
            }),
        }
    
    dynamodb.Table(TABLE_NAME).update_item( 
        Key={"order_id": event["detail"]["order_id"]}, 
        UpdateExpression="SET order_status = :s", 
        ExpressionAttributeValues={":s": "shipped"}
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "order is shipped"
        }),
    }
