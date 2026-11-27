"""Attachment rollout guards with synthetic AWS; no credentials or live I/O."""
import copy
import json
import tempfile
import unittest

from test_environment_settings import FakeAws, PREFIX, SECRET
import wire_live_bunny_settings as shared
import wire_session_attachment_settings as wire


class AttachmentSettingsTests(unittest.TestCase):
    def setUp(self):
        self.aws = FakeAws()
        template = copy.deepcopy(self.aws.definitions[PREFIX + 'night-api:1'])
        arn = PREFIX + 'learner-api:1'
        self.aws.services['learner-api'] = {**copy.deepcopy(self.aws.services['night-api']),
            'serviceName': 'learner-api', 'taskDefinition': arn, 'desiredCount': 3}
        self.aws.definitions[arn] = {**template, 'family': 'learner-api', 'taskDefinitionArn': arn}
        for service in self.aws.services.values():
            service['deployments'] = [{'rolloutState': 'COMPLETED'}]
        self.aws.secret_values.update(dict(zip(wire.KEYS,
            ('synthetic-private-zone', 'synthetic-zone-password', 'storage.bunnycdn.com'))))

    def plan(self):
        return wire.build_plan(self.aws, 'example-cluster', '123456789012')

    def assert_no_writes(self):
        self.assertFalse(any(operation in ('register-task-definition', 'update-service')
                             for _, operation, _ in self.aws.calls))

    def test_read_only_plan_is_redacted_and_changes_only_missing_bindings(self):
        plan = self.plan()
        self.assert_no_writes()
        self.assertNotIn('synthetic-zone-password', json.dumps(shared.public_plan(plan)))
        self.assertEqual([row['service'] for row in plan['services']], list(wire.TARGETS))
        for row in plan['services']:
            restored = copy.deepcopy(row['proposed'])
            restored['containerDefinitions'][0]['secrets'] = [item for item in restored['containerDefinitions'][0]['secrets']
                                                             if item['name'] not in row['added_names']]
            self.assertEqual(restored, row['original'])

    def test_apply_is_idempotent_and_preserves_counts_settings_and_collection_switch(self):
        values = copy.deepcopy(self.aws.secret_values)
        counts = {name: row['desiredCount'] for name, row in self.aws.services.items()}
        plan = self.plan()
        with tempfile.TemporaryDirectory() as folder:
            shared.apply_plan(self.aws, plan, shared.fingerprint(plan), folder)
        self.assertTrue(all(not row['added_names'] for row in self.plan()['services']))
        self.assertEqual(self.aws.secret_values, values)
        self.assertEqual({name: row['desiredCount'] for name, row in self.aws.services.items()}, counts)

    def test_bad_settings_or_account_never_register_a_definition(self):
        mutations = (
            lambda: self.aws.secret_values.pop(wire.KEYS[1]),
            lambda: self.aws.secret_values.update({wire.KEYS[2]: 'attacker.invalid'}),
            lambda: self.aws.secret_values.update({wire.KEYS[0]: '../other-zone'}),
            lambda: self.aws.secret_values.update({wire.KEYS[1]: self.aws.secret_values[shared.KEYS[1]]}),
        )
        for mutation in mutations:
            self.setUp()
            mutation()
            with self.assertRaises(shared.ConfigurationError):
                self.plan()
            self.assert_no_writes()
        with self.assertRaises(shared.ConfigurationError):
            wire.build_plan(self.aws, 'example-cluster', '000000000000')
        self.assert_no_writes()

    def test_conflicting_binding_plain_value_and_active_or_overlapping_worker_block(self):
        mutations = (
            lambda: self.aws.definitions[PREFIX + 'learner-api:1']['containerDefinitions'][0]['secrets'].append(
                {'name': wire.KEYS[1], 'valueFrom': SECRET + ':OTHER_KEY::'}),
            lambda: self.aws.definitions[PREFIX + 'learner-api:1']['containerDefinitions'][0]['environment'].append(
                {'name': wire.KEYS[0], 'value': 'other-zone'}),
            lambda: self.aws.services['night-api'].update(deployments=[{'rolloutState': 'IN_PROGRESS'}]),
            lambda: self.aws.services['session-worker']['deploymentConfiguration'].update(maximumPercent=200),
        )
        for mutation in mutations:
            self.setUp()
            mutation()
            with self.assertRaises(shared.ConfigurationError):
                self.plan()
            self.assert_no_writes()

    def test_late_update_failure_restores_all_previous_services(self):
        before = {name: row['taskDefinition'] for name, row in self.aws.services.items()}
        plan = self.plan()
        self.aws.fail_service = 'session-worker'
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(shared.ConfigurationError):
                shared.apply_plan(self.aws, plan, shared.fingerprint(plan), folder)
        self.assertEqual({name: row['taskDefinition'] for name, row in self.aws.services.items()}, before)

    def test_stale_review_fingerprint_blocks_every_write(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(shared.ConfigurationError):
                shared.apply_plan(self.aws, plan, 'stale', folder)
        self.assert_no_writes()


if __name__ == '__main__':
    unittest.main()
