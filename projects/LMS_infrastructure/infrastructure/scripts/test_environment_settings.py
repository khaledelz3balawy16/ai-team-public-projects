"""Synthetic tests: no AWS connection or real environment values."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

import env_to_tfvars as export
import wire_live_bunny_settings as wire

SECRET = 'arn:aws:secretsmanager:eu-west-2:123456789012:secret:example-AbCdEf'
PREFIX = 'arn:aws:ecs:eu-west-2:123456789012:task-definition/'


class FakeAws:
    def __init__(self):
        self.calls = []
        self.fail_service = None
        self.definitions = {}
        self.services = {}
        for name in ('curriculum-api', *wire.TARGETS):
            arn = PREFIX + name + ':1'
            self.services[name] = {'serviceName': name, 'status': 'ACTIVE', 'taskDefinition': arn,
                'desiredCount': 0 if name == 'night-api' else 1,
                'deploymentConfiguration': {'minimumHealthyPercent': 0, 'maximumPercent': 100}}
            secrets = [{'name': 'BUNNY_STREAM_API_KEY', 'valueFrom': SECRET + ':BUNNY_STREAM_API_KEY::'}]
            if name == 'curriculum-api':
                secrets += [{'name': key, 'valueFrom': SECRET + ':' + key + '::'} for key in wire.KEYS]
            self.definitions[arn] = {'taskDefinitionArn': arn, 'revision': 1, 'status': 'ACTIVE',
                'family': name, 'cpu': '1024', 'memory': '3072', 'networkMode': 'awsvpc',
                'taskRoleArn': 'example-task-role', 'executionRoleArn': 'example-execution-role',
                'requiresCompatibilities': ['FARGATE'],
                'containerDefinitions': [{'name': 'worker' if name == 'session-worker' else 'app',
                    'image': 'example.invalid/image:existing', 'command': ['existing', 'command'],
                    'environment': [{'name': 'DJANGO_DEBUG', 'value': 'false'}], 'secrets': secrets}]}
        self.secret_values = {wire.KEYS[0]: '796471', wire.KEYS[1]: 'synthetic-key-must-stay-private'}

    def __call__(self, service, operation, payload):
        self.calls.append((service, operation, copy.deepcopy(payload)))
        if operation == 'get-caller-identity':
            return {'Account': '123456789012'}
        if operation == 'describe-services':
            return {'services': [copy.deepcopy(self.services[name]) for name in payload['services']]}
        if operation == 'describe-task-definition':
            return {'taskDefinition': copy.deepcopy(self.definitions[payload['taskDefinition']])}
        if operation == 'CHANGE_ME':
            return {'SecretString': json.dumps(self.secret_values)}
        if operation == 'register-task-definition':
            arn = PREFIX + payload['family'] + ':2'
            self.definitions[arn] = {**copy.deepcopy(payload), 'taskDefinitionArn': arn, 'revision': 2}
            return {'taskDefinition': {'taskDefinitionArn': arn}}
        if operation == 'update-service':
            if payload['service'] == self.fail_service:
                self.fail_service = None
                raise wire.ConfigurationError('ecs:update-service:AccessDeniedException')
            self.services[payload['service']]['taskDefinition'] = payload['taskDefinition']
            return {'service': copy.deepcopy(self.services[payload['service']])}
        raise AssertionError('Unexpected operation')


class ExportTests(unittest.TestCase):
    def test_production_reference_preserves_missing_and_conflicting_values(self):
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / 'local.env'
            prod = Path(folder) / 'production.env'
            local.write_text('FRONTEND_URL=http://localhost:3000\nTOKEN=CHANGE_ME\nNEW_FLAG=true\n')
            prod.write_text('FRONTEND_URL=https://example.invalid\nTOKEN=CHANGE_ME\nPROD_ONLY=CHANGE_ME\n')
            values, _ = export.export_values(local, prod)
            self.assertEqual(values['FRONTEND_URL'], 'https://example.invalid')
            self.assertEqual(values['TOKEN'], 'CHANGE_ME')
            self.assertEqual(values['PROD_ONLY'], 'CHANGE_ME')
            self.assertEqual(values['NEW_FLAG'], 'true')

    def test_export_escapes_terraform_interpolation_without_printing_values(self):
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / 'local.env'
            output = Path(folder) / 'private.tfvars'
            local.write_text('TOKEN=synthetic-${must-not-evaluate}-%{or-this}\n')
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                export.main(local, output)
            self.assertIn('$${must-not-evaluate}', output.read_text())
            self.assertIn('%%{or-this}', output.read_text())
            self.assertNotIn('synthetic-', captured.getvalue())

    def test_never_overwrites_input_or_exports_an_empty_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / 'local.env'
            local.write_text('TOKEN=CHANGE_ME\n')
            with self.assertRaises(ValueError):
                export.main(local, local)
            empty = Path(folder) / 'empty.env'
            empty.write_text('# empty\n')
            with self.assertRaises(ValueError):
                export.main(local, Path(folder) / 'out.tfvars', empty)
            self.assertEqual(local.read_text(), 'TOKEN=CHANGE_ME\n')

    def test_parser_retains_effective_duplicate_rules_and_rejects_value_fragments(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'local.env'
            path.write_text('TOKEN=first\nTOKEN=second\nMICROSOFT_CLIENT_ID=first\nMICROSOFT_CLIENT_ID=last\n"private_key": "synthetic==\n')
            values, skipped = export.parse(path)
            self.assertEqual(values, {'TOKEN': 'CHANGE_ME', 'MICROSOFT_CLIENT_ID': 'last'})
            self.assertEqual(skipped, 1)


class WiringTests(unittest.TestCase):
    def setUp(self):
        self.aws = FakeAws()

    def plan(self):
        return wire.build_plan(self.aws, 'example-cluster', '123456789012')

    def test_default_plan_reads_only_and_public_output_contains_no_secret(self):
        plan = self.plan()
        self.assertFalse(any(operation in ('register-task-definition', 'update-service') for _, operation, _ in self.aws.calls))
        self.assertNotIn('synthetic-key-must-stay-private', json.dumps(wire.public_plan(plan)))
        self.assertEqual([row['added_names'] for row in plan['services']], [list(wire.KEYS), list(wire.KEYS)])

    def test_plan_preserves_all_fields_except_the_two_missing_bindings(self):
        for item in self.plan()['services']:
            proposed = copy.deepcopy(item['proposed'])
            container = proposed['containerDefinitions'][0]
            container['secrets'] = [row for row in container['secrets'] if row['name'] not in wire.KEYS]
            self.assertEqual(proposed, item['original'])

    def test_apply_updates_only_definition_arns_and_is_idempotent(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as folder:
            result = wire.apply_plan(self.aws, plan, wire.fingerprint(plan), folder)
            self.assertEqual(result['updated_services'], list(wire.TARGETS))
            self.assertTrue(Path(result['backup']).exists())
        for _, operation, payload in self.aws.calls:
            if operation == 'update-service':
                self.assertEqual(set(payload), {'cluster', 'service', 'taskDefinition'})
        self.assertEqual(self.aws.services['night-api']['desiredCount'], 0)
        self.assertTrue(all(not row['added_names'] for row in self.plan()['services']))

    def test_wrong_account_missing_secret_or_conflicting_binding_blocks_all_writes(self):
        with self.assertRaises(wire.ConfigurationError):
            wire.build_plan(self.aws, 'example-cluster', 'wrong-account')
        self.aws.secret_values.pop(wire.KEYS[1])
        with self.assertRaises(wire.ConfigurationError):
            self.plan()
        self.assertFalse(any(operation == 'register-task-definition' for _, operation, _ in self.aws.calls))

    def test_existing_conflict_and_overlapping_worker_are_rejected(self):
        worker = self.aws.definitions[PREFIX + 'session-worker:1']
        worker['containerDefinitions'][0]['secrets'].append({'name': wire.KEYS[0], 'valueFrom': 'different-reference'})
        with self.assertRaises(wire.ConfigurationError):
            self.plan()
        worker['containerDefinitions'][0]['secrets'].pop()
        self.aws.services['session-worker']['deploymentConfiguration']['maximumPercent'] = 200
        with self.assertRaises(wire.ConfigurationError):
            self.plan()

    def test_changed_plan_or_concurrent_deployment_cannot_overwrite_newer_settings(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(wire.ConfigurationError):
                wire.apply_plan(self.aws, plan, 'outdated-fingerprint', folder)
            self.aws.definitions[PREFIX + 'session-worker:1']['containerDefinitions'][0]['image'] = 'newer-image'
            with self.assertRaises(wire.ConfigurationError):
                wire.apply_plan(self.aws, plan, wire.fingerprint(plan), folder)
        self.assertFalse(any(operation == 'register-task-definition' for _, operation, _ in self.aws.calls))

    def test_failed_update_restores_previous_service_definitions(self):
        plan = self.plan()
        self.aws.fail_service = 'night-api'
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(wire.ConfigurationError, 'restored.*AccessDeniedException'):
                wire.apply_plan(self.aws, plan, wire.fingerprint(plan), folder)
        self.assertEqual(self.aws.services['session-worker']['taskDefinition'], PREFIX + 'session-worker:1')
        self.assertEqual(self.aws.services['night-api']['taskDefinition'], PREFIX + 'night-api:1')


if __name__ == '__main__':
    unittest.main()
