import os
import json
import requests
import uuid
from unittest import TestCase
import aws_iatk

class TestTrace(TestCase):
    aws_region = os.environ.get("AWS_REGION")
    if(aws_region is None):
        raise Exception("AWS_REGION environment variable is required")
    iatk_client = aws_iatk.AwsIatk(region=aws_region)

    listener_id = None
    stack_outputs = None

    def setUp(self):
        self.stack_outputs = self.iatk_client.get_stack_outputs(
            stack_name=os.environ.get("TEST_STACK_NAME"),
            output_names=["OrderApi", "PrepareShippingEventRule", "OrderFunction", "ShippingFunction"]
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

    def test_order_trace(self):        
        sample_order = { 
            "order_id": str(uuid.uuid4()),
            "amount": 100 
        }
        expectedTraceTree = [
            [
                { "origin": "AWS::ApiGateway::Stage", "name": "iatk-demo/Proda" },
                { "origin": "AWS::Lambda", "name": self.stack_outputs["OrderFunction"] },
                { "origin": "AWS::Lambda::Function", "name": self.stack_outputs["OrderFunction"] },
                { "origin": "AWS::DynamoDB::Table", "name": "DynamoDB" },
            ],
            [
                { "origin": "AWS::ApiGateway::Stage", "name": "iatk-demo/Prod" },
                { "origin": "AWS::Lambda", "name": self.stack_outputs["OrderFunction"] },
                { "origin": "AWS::Lambda::Function", "name": self.stack_outputs["OrderFunction"] },
                { "origin": "AWS::Events", "name": "Events" },
                { "origin": "AWS::Lambda", "name": self.stack_outputs["ShippingFunction"] },
                { "origin": "AWS::Lambda::Function", "name": self.stack_outputs["ShippingFunction"] },
                { "origin": "AWS::DynamoDB::Table", "name": "DynamoDB" },
            ]
        ]
 
        response = requests.post(self.stack_outputs["OrderApi"], json=sample_order)
        self.assertEqual(response.status_code, requests.codes.ok)
        trace_id = response.headers['X-Amzn-Trace-Id']
        
        self.iatk_client.poll_events(
            listener_id=self.listener_id,
            wait_time_seconds=20,
            max_number_of_messages=1,
        )

        def assertion(output):
            tree = output.trace_tree
            self.assertEqual(len(tree.paths), 2)
            for i, path in enumerate(tree.paths):
                for j, seg in enumerate(path):
                    self.assertIsNone(seg.error)
                    self.assertIsNone(seg.fault)
                    self.assertEqual(seg.origin, expectedTraceTree[i][j]["origin"])
                    self.assertEqual(seg.name, expectedTraceTree[i][j]["name"])
        
        self.assertTrue(self.iatk_client.retry_get_trace_tree_until(
            tracing_header=trace_id,
            assertion_fn=assertion,
            timeout_seconds=20,
        ))
