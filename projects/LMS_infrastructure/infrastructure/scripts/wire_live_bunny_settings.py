"""Plan (default) or apply only the two existing LiveSessions secret bindings.

Uses the current curriculum-api bindings as the reference. It never changes
secret values, task images, commands, roles, desired counts or schedules.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

KEYS = ('BUNNY_LIVE_STREAM_LIBRARY_ID', 'BUNNY_LIVE_STREAM_API_KEY')
TARGETS = ('session-worker', 'night-api')
FIELDS = {'family', 'taskRoleArn', 'executionRoleArn', 'networkMode', 'containerDefinitions',
    'volumes', 'placementConstraints', 'requiresCompatibilities', 'cpu', 'memory', 'tags',
    'pidMode', 'ipcMode', 'proxyConfiguration', 'inferenceAccelerators',
    'ephemeralStorage', 'runtimePlatform', 'enableFaultInjection'}
RESPONSE_FIELDS = {'taskDefinitionArn', 'revision', 'status', 'requiresAttributes',
    'compatibilities', 'registeredAt', 'registeredBy', 'deregisteredAt'}


class ConfigurationError(RuntimeError):
    pass


class AwsCli:
    def __init__(self, region):
        self.region = region

    def __call__(self, service, operation, payload):
        allowed = {('sts', 'get-caller-identity'), ('ecs', 'describe-services'),
            ('ecs', 'describe-task-definition'), ('secretsmanager', 'CHANGE_ME'),
            ('ecs', 'register-task-definition'), ('ecs', 'update-service')}
        if (service, operation) not in allowed:
            raise ConfigurationError('Unsupported AWS operation')
        with tempfile.TemporaryDirectory(prefix='lms-bunny-settings-') as directory:
            request = Path(directory) / 'request.json'
            request.write_text(json.dumps(payload), encoding='utf-8')
            os.chmod(request, 0o600)
            result = subprocess.run(['aws', service, operation, '--cli-input-json',
                'file://' + str(request), '--region', self.region, '--output', 'json', '--no-cli-pager'],
                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90,
                env={**os.environ, 'AWS_PAGER': '', 'AWS_CLI_AUTO_PROMPT': 'off'})
        if result.returncode:
            code = re.search(r'\(([A-Za-z0-9_.]+)\)', result.stderr)
            raise ConfigurationError(service + ':' + operation + ':' + (code.group(1) if code else 'failed'))
        return json.loads(result.stdout)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def registration(definition):
    if set(definition) - FIELDS - RESPONSE_FIELDS:
        raise ConfigurationError('Unknown task-definition fields; manual review required')
    return {key: copy.deepcopy(value) for key, value in definition.items() if key in FIELDS}


def service_definition(client, cluster, name):
    response = client('ecs', 'describe-services', {'cluster': cluster, 'services': [name]})
    if response.get('failures') or len(response.get('services', [])) != 1:
        raise ConfigurationError('Service unavailable: ' + name)
    service = response['services'][0]
    if service.get('status') != 'ACTIVE':
        raise ConfigurationError('Service is not active: ' + name)
    response = client('ecs', 'describe-task-definition', {'taskDefinition': service['taskDefinition'], 'include': ['TAGS']})
    definition = response['taskDefinition']
    if response.get('tags'):
        definition = {**definition, 'tags': response['tags']}
    if len(definition['containerDefinitions']) != 1:
        raise ConfigurationError('Expected one container: ' + name)
    registration(definition)
    return service, definition


def build_plan(client, cluster, expected_account):
    if client('sts', 'get-caller-identity', {})['Account'] != expected_account:
        raise ConfigurationError('Unexpected AWS account')
    _, source = service_definition(client, cluster, 'curriculum-api')
    source_container = source['containerDefinitions'][0]
    refs = {}
    for key in KEYS:
        found = [item['valueFrom'] for item in source_container.get('secrets', []) if item['name'] == key]
        if len(found) != 1 or any(item['name'] == key for item in source_container.get('environment', [])):
            raise ConfigurationError('Missing or conflicting source binding: ' + key)
        parts = found[0].split(':')
        if len(parts) != 10 or parts[2] != 'secretsmanager' or parts[7:] != [key, '', '']:
            raise ConfigurationError('Unexpected secret reference format: ' + key)
        refs[key] = found[0]
    secret_ids = {':'.join(ref.split(':')[:7]) for ref in refs.values()}
    if len(secret_ids) != 1:
        raise ConfigurationError('LiveSessions settings must use the existing shared secret')
    secret_id = next(iter(secret_ids))
    values = json.loads(client('secretsmanager', 'CHANGE_ME', {'SecretId': secret_id})['SecretString'])
    if str(values.get(KEYS[0], '')).strip() != '796471' or not str(values.get(KEYS[1], '')).strip():
        raise ConfigurationError('Expected LiveSessions library/key not available; values withheld')
    plans = []
    for name in TARGETS:
        service, current = service_definition(client, cluster, name)
        if name == 'session-worker':
            deployment = service.get('deploymentConfiguration', {})
            if deployment.get('minimumHealthyPercent') != 0 or deployment.get('maximumPercent') != 100:
                raise ConfigurationError('Worker must stop its old task before starting a replacement')
        proposed = registration(current)
        container = proposed['containerDefinitions'][0]
        existing = {item['name']: item['valueFrom'] for item in container.get('secrets', [])}
        if not any(ref.startswith(secret_id + ':') for ref in existing.values()):
            raise ConfigurationError('Target does not already use the shared secret: ' + name)
        added = []
        for key in KEYS:
            if any(item['name'] == key for item in container.get('environment', [])):
                raise ConfigurationError('Conflicting plain setting on ' + name + ': ' + key)
            if key in existing and existing[key] != refs[key]:
                raise ConfigurationError('Conflicting secret binding on ' + name + ': ' + key)
            if key not in existing:
                container.setdefault('secrets', []).append({'name': key, 'valueFrom': refs[key]})
                added.append(key)
        plans.append({'service': name, 'current_arn': service['taskDefinition'],
            'desired_count': service['desiredCount'], 'original': registration(current),
            'proposed': proposed, 'added_names': added})
    return {'cluster': cluster, 'account': expected_account, 'source_bindings': refs, 'services': plans}


def public_plan(plan):
    return {'plan_sha256': fingerprint(plan), 'server_writes': 0,
        'secret_value_changes': 0, 'preserved': ['images', 'commands', 'roles', 'existing settings', 'desired counts', 'schedules'],
        'services': [{'service': item['service'], 'current_definition': item['current_arn'].rsplit('/', 1)[-1],
            'desired_count': item['desired_count'], 'add_secret_bindings': item['added_names'],
            'resource_change': ({key: {'before': item['original'].get(key), 'after': item['proposed'].get(key)}
                for key in ('cpu', 'memory') if item['original'].get(key) != item['proposed'].get(key)} or None)}
            for item in plan['services']]}


def apply_plan(client, plan, expected_fingerprint, backup_dir):
    if fingerprint(plan) != expected_fingerprint:
        raise ConfigurationError('Plan has changed; review the fresh plan before applying')
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / ('live-bunny-definitions-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    with backup.open('x', encoding='utf-8') as stream:
        json.dump(plan, stream, indent=2)
    os.chmod(backup, 0o600)
    updated = []
    try:
        for item in plan['services']:
            if item['proposed'] == item['original']:
                continue
            # Guard against another operator deploying since the plan was read.
            service, definition = service_definition(client, plan['cluster'], item['service'])
            if service['taskDefinition'] != item['current_arn'] or registration(definition) != item['original']:
                raise ConfigurationError('Service changed concurrently: ' + item['service'])
            registered = client('ecs', 'register-task-definition', item['proposed'])['taskDefinition']['taskDefinitionArn']
            # Track intent first: an ambiguous update failure must restore the previous ARN.
            updated.append(item)
            client('ecs', 'update-service', {'cluster': plan['cluster'], 'service': item['service'], 'taskDefinition': registered})
    except Exception as error:
        rollback_failed = []
        for item in reversed(updated):
            try:
                client('ecs', 'update-service', {'cluster': plan['cluster'], 'service': item['service'], 'taskDefinition': item['current_arn']})
            except Exception:
                rollback_failed.append(item['service'])
        if rollback_failed:
            raise ConfigurationError('Apply failed; rollback needs attention: ' + ', '.join(rollback_failed)) from None
        reason = str(error) if isinstance(error, ConfigurationError) else type(error).__name__
        raise ConfigurationError('Apply failed; previous service definitions restored (' + reason + ')') from None
    return {'updated_services': [item['service'] for item in updated], 'backup': str(backup),
        'secret_value_changes': 0, 'desired_count_changes': 0, 'schedule_changes': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', default='eu-west-2')
    parser.add_argument('--cluster', default='lms-staging-cluster')
    parser.add_argument('--expected-account', default='824892928722')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--expected-plan')
    parser.add_argument('--backup-dir')
    args = parser.parse_args()
    if args.apply and not (args.expected_plan and args.backup_dir):
        parser.error('--apply requires --expected-plan and a private --backup-dir')
    client = AwsCli(args.region)
    try:
        plan = build_plan(client, args.cluster, args.expected_account)
        result = apply_plan(client, plan, args.expected_plan, args.backup_dir) if args.apply else public_plan(plan)
    except (ConfigurationError, ValueError, KeyError) as error:
        # ConfigurationError messages contain setting names/operation codes only.
        print(json.dumps({'error': str(error) if isinstance(error, ConfigurationError) else type(error).__name__}))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
