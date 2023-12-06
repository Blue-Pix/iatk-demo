import os
import json
import requests
import uuid
from unittest import TestCase

import aws_iatk

class TestMockEvent(TestCase):
    aws_region = os.environ.get("AWS_REGION")
    if(aws_region is None):
        raise Exception("AWS_REGION environment variable is required")
    iatk_client = aws_iatk.AwsIatk(region=aws_region)

    listener_id = None
    stack_outputs = None

    def setUp(self):
        self.stack_outputs = self.iatk_client.get_stack_outputs(
            stack_name=os.environ.get("TEST_STACK_NAME"),
            output_names=["OrderApi","PrepareShippingEventRule", "CustomEventRegistry", "CreateOrderEventSchema"]
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

    def test_create_order_with_mock_event(self):        
        expected_event = {
            "source": "iatk_demo.order_service",
            "detail-type": "order_created"
        }

        def set_mock_event_properties(event):
            event["order_id"] = str(uuid.uuid4())
            event["amount"] = 100
            return event
        
        mock_event = self.iatk_client.generate_mock_event(
            registry_name=self.stack_outputs["CustomEventRegistry"],
            schema_name=self.stack_outputs["CreateOrderEventSchema"],
            contexts=[set_mock_event_properties],
        ).event

        response = requests.post(self.stack_outputs["OrderApi"], json=mock_event)
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
        self.assertEqual(actual_event["detail"]["order_id"], mock_event["order_id"])
        self.assertEqual(actual_event["detail"]["order_status"], "created")
