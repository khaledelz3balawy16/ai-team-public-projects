"""Existing service configuration is preserved; all AWS operations are doubled."""
import copy
import json
import tempfile
import unittest

from test_environment_settings import FakeAws, PREFIX
import wire_live_bunny_settings as old
import wire_recording_settings as wire


class RecordingSettingsTests(unittest.TestCase):
    def setUp(self):
        self.aws = FakeAws()
        template = copy.deepcopy(self.aws.definitions[PREFIX + 'night-api:1'])
        for name in ('learner-api', 'coach-api'):
            arn = PREFIX + name + ':1'
            self.aws.services[name] = {**copy.deepcopy(self.aws.services['night-api']),
                                      'serviceName': name, 'taskDefinition': arn}
            self.aws.definitions[arn] = {**copy.deepcopy(template), 'family': name, 'taskDefinitionArn': arn}
        for service in self.aws.services.values():
            service['deployments'] = [{'rolloutState': 'COMPLETED'}]
        self.aws.secret_values.update({key: 'synthetic-private-value' for key in wire.LIVE + wire.COACH})
        self.aws.secret_values.update({wire.LIVE[0]: '796471', wire.COACH[0]: '999001'})
        self.aws.secret_values.update({key: 'false' for key in wire.LIVE_FLAGS + wire.COACH_FLAGS})

    def plan(self):
        return wire.build_plan(self.aws, 'example-cluster', '123456789012')

    def test_plan_is_read_only_redacted_and_preserves_every_other_field(self):
        plan = self.plan()
        self.assertNotIn('synthetic-private-value', json.dumps(old.public_plan(plan)))
        self.assertFalse(any(operation == 'register-task-definition' for _, operation, _ in self.aws.calls))
        for row in plan['services']:
            restored = copy.deepcopy(row['proposed'])
            restored['containerDefinitions'][0]['secrets'] = [item for item in restored['containerDefinitions'][0]['secrets']
                                                             if item['name'] not in row['added_names']]
            self.assertEqual(restored, row['original'])

    def test_apply_is_idempotent_and_never_changes_switch_values_or_desired_counts(self):
        values = copy.deepcopy(self.aws.secret_values)
        counts = {name: row['desiredCount'] for name, row in self.aws.services.items()}
        plan = self.plan()
        with tempfile.TemporaryDirectory() as folder:
            old.apply_plan(self.aws, plan, old.fingerprint(plan), folder)
        self.assertTrue(all(not row['added_names'] for row in self.plan()['services']))
        self.assertEqual(self.aws.secret_values, values)
        self.assertEqual({name: row['desiredCount'] for name, row in self.aws.services.items()}, counts)

    def test_missing_settings_shared_library_and_active_release_block_writes(self):
        for mutate in (
            lambda: self.aws.secret_values.pop(wire.LIVE[2]),
            lambda: self.aws.secret_values.update({wire.COACH[0]: '796471'}),
            lambda: self.aws.services['coach-api'].update(deployments=[{'rolloutState': 'IN_PROGRESS'}]),
        ):
            self.setUp()
            mutate()
            with self.assertRaises(wire.ConfigurationError):
                self.plan()
            self.assertFalse(any(operation == 'register-task-definition' for _, operation, _ in self.aws.calls))

    def test_resource_only_change_is_applied_after_bindings_are_already_present(self):
        initial = self.plan()
        with tempfile.TemporaryDirectory() as folder:
            old.apply_plan(self.aws, initial, old.fingerprint(initial), folder)
            plan = wire.build_plan(self.aws, 'example-cluster', '123456789012', 512, 2048)
            self.assertTrue(all(not row['added_names'] for row in plan['services']))
            changed = [row for row in plan['services'] if row['proposed'] != row['original']]
            self.assertEqual([row['service'] for row in changed], ['session-worker'])
            proposal = copy.deepcopy(changed[0]['proposed'])
            proposal.update(cpu='1024', memory='3072')
            self.assertEqual(proposal, changed[0]['original'])
            result = old.apply_plan(self.aws, plan, old.fingerprint(plan), folder)
            self.assertEqual(result['updated_services'], ['session-worker'])

    def test_incomplete_or_unreviewed_resource_profile_is_rejected(self):
        for cpu, memory in ((512, None), (None, 2048), (256, 1024), (512, 3072)):
            with self.assertRaises(wire.ConfigurationError):
                wire.build_plan(self.aws, 'example-cluster', '123456789012', cpu, memory)


if __name__ == '__main__':
    unittest.main()
