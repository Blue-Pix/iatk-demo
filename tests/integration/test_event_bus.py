import os
import json
import requests
import uuid
from unittest import TestCase

import aws_iatk

class TestEventBus(TestCase):
    aws_region = os.environ.get("AWS_REGION")
    if(aws_region is None):
        raise Exception("AWS_REGION environment variable is required")
    iatk_client = aws_iatk.AwsIatk(region=aws_region)

    listener_id = None
    stack_outputs = None

    def setUp(self):
        self.stack_outputs = self.iatk_client.get_stack_outputs(
            stack_name=os.environ.get("TEST_STACK_NAME"),
            output_names=["OrderApi","PrepareShippingEventRule"]
        ).outputs

        listener = self.iatk_client.add_listener(
            event_bus_name="default",
            rule_name=self.stack_outputs["PrepareShippingEventRule"]
        )
        self.listener_id = listener.id

    def tearDown(self):
        self.iatk_client.remove_listeners(
            ids=[self.listener_id],
        )

    def test_order_created_event_published(self):        
        expected_event = {
            "source": "iatk_demo.order_service",
            "detail-type": "order_created"
        }
        sample_order = { 
            "order_id": str(uuid.uuid4()),
            "amount": 100 
        }
 
        response = requests.post(self.stack_outputs["OrderApi"], json=sample_order)
        self.assertEqual(response.status_code, requests.codes.ok)

        poll_outputs = self.iatk_client.poll_events(
            listener_id=self.listener_id,
            wait_time_seconds=20,
            max_number_of_messages=1,
        )

        self.assertEqual(len(poll_outputs.events), 1)
        
        actual_event = json.loads(poll_outputs.events[0])
        self.assertEqual(actual_event["source"], expected_event["source"])
        self.assertEqual(actual_event["detail-type"], expected_event["detail-type"])
        self.assertEqual(actual_event["detail"]["order_id"], sample_order["order_id"])
        self.assertEqual(actual_event["detail"]["order_status"], "created")
        