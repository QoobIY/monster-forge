"""Constructor actions reject malformed requests before running authoring work."""
import json
import unittest
from unittest.mock import patch

from monsterforge import create_app


class ConstructorApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_actions_return_json_errors_for_invalid_request_shapes(self):
        for action in ('preview', 'save', 'export'):
            for payload in (None, [], 'settings', 1, {'race': []}, {'race': {}}, {'race': True}):
                with self.subTest(action=action, payload=payload):
                    response = self.client.post('/creature-workshop/constructor/' + action,
                                                data=json.dumps(payload),
                                                content_type='application/json')
                    self.assertEqual(response.status_code, 400)
                    self.assertIsInstance(response.json['error'], str)

    def test_parse_and_size_errors_use_the_same_json_response_contract(self):
        cases = (({'data': '{broken', 'content_type': 'application/json'}, 400),
                 ({'data': '{}', 'content_type': 'text/plain'}, 415),
                 ({'data': 'x' * 16385, 'content_type': 'application/json'}, 413))
        for action in ('preview', 'save', 'export'):
            for arguments, status in cases:
                with self.subTest(action=action, status=status):
                    response = self.client.post('/creature-workshop/constructor/' + action,
                                                **arguments)
                    self.assertEqual(response.status_code, status)
                    self.assertIsInstance(response.json['error'], str)

    def test_valid_requests_are_dispatched_without_changing_settings(self):
        from monsterforge.workshop_constructor import default_settings
        settings = default_settings()
        for action in ('preview', 'save'):
            with self.subTest(action=action), patch('monsterforge.workshop_constructor.' + action,
                                                   return_value={'result': action}) as operation:
                response = self.client.post('/creature-workshop/constructor/' + action,
                                            json=settings)
                self.assertEqual(response.json, {'result': action})
                operation.assert_called_once_with(settings)
        with (patch('monsterforge.workshop_constructor.export_bundle', return_value=b'archive') as operation,
              self.client.post('/creature-workshop/constructor/export', json=settings) as response):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'application/zip')
            self.assertEqual(response.data, b'archive')
            operation.assert_called_once_with(settings)
