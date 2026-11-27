"""Bind private attachment storage to existing services; default is read-only.

This does not enable Microsoft chat collection, change secret values, or create
storage. Apply only from reviewed main after the private zone is verified.
"""
import argparse
import copy
import json
import re

from wire_live_bunny_settings import (
    AwsCli, ConfigurationError, apply_plan, public_plan, registration,
    service_definition,
)

KEYS = ('BUNNY_SESSION_ATTACHMENTS_ZONE', 'BUNNY_SESSION_ATTACHMENTS_KEY',
        'BUNNY_SESSION_ATTACHMENTS_HOST')
TARGETS = ('curriculum-api', 'learner-api', 'session-worker', 'night-api')
HOSTS = frozenset(('storage.bunnycdn.com', 'uk.storage.bunnycdn.com',
    'ny.storage.bunnycdn.com', 'la.storage.bunnycdn.com', 'sg.storage.bunnycdn.com',
    'se.storage.bunnycdn.com', 'br.storage.bunnycdn.com', 'jh.storage.bunnycdn.com',
    'syd.storage.bunnycdn.com'))


def build_plan(client, cluster, expected_account):
    if client('sts', 'get-caller-identity', {})['Account'] != expected_account:
        raise ConfigurationError('Unexpected AWS account')
    _, source = service_definition(client, cluster, 'curriculum-api')
    anchor = 'BUNNY_LIVE_STREAM_LIBRARY_ID'
    refs = [row['valueFrom'] for row in source['containerDefinitions'][0].get('secrets', [])
            if row['name'] == anchor]
    if len(refs) != 1:
        raise ConfigurationError('Missing authoritative curriculum secret binding')
    parts = refs[0].split(':')
    if len(parts) != 10 or parts[2] != 'secretsmanager' or parts[7:] != [anchor, '', '']:
        raise ConfigurationError('Unexpected shared secret reference format')
    secret_id = ':'.join(parts[:7])
    values = json.loads(client('secretsmanager', 'CHANGE_ME', {'SecretId': secret_id})['SecretString'])
    if (not all(isinstance(values.get(key), str) and values[key].strip() for key in KEYS)
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', values[KEYS[0]])
            or values[KEYS[2]] not in HOSTS):
        raise ConfigurationError('Private attachment storage settings are incomplete or invalid; values withheld')
    if any(values[KEYS[1]] == values.get(name) for name in (
            'BUNNY_STREAM_API_KEY', 'BUNNY_LIVE_STREAM_API_KEY',
            'BUNNY_COACH_STREAM_API_KEY', 'BUNNY_ACCOUNT_API_KEY')):
        raise ConfigurationError('Attachment storage must use its own zone key')
    plans = []
    for name in TARGETS:
        service, current = service_definition(client, cluster, name)
        deployments = service.get('deployments', [])
        if len(deployments) != 1 or deployments[0].get('rolloutState') != 'COMPLETED':
            raise ConfigurationError('Wait for the active release before wiring: ' + name)
        if name == 'session-worker':
            policy = service.get('deploymentConfiguration', {})
            if policy.get('minimumHealthyPercent') != 0 or policy.get('maximumPercent') != 100:
                raise ConfigurationError('Worker must stop before its replacement starts')
        proposed = registration(current)
        container = proposed['containerDefinitions'][0]
        existing = {row['name']: row['valueFrom'] for row in container.get('secrets', [])}
        if not any(ref.startswith(secret_id + ':') for ref in existing.values()):
            raise ConfigurationError('Target does not already use the shared secret: ' + name)
        added = []
        for key in KEYS:
            ref = secret_id + ':' + key + '::'
            if any(row['name'] == key for row in container.get('environment', [])):
                raise ConfigurationError('Conflicting plain attachment setting on ' + name + ': ' + key)
            if key in existing and existing[key] != ref:
                raise ConfigurationError('Conflicting attachment secret on ' + name + ': ' + key)
            if key not in existing:
                container.setdefault('secrets', []).append({'name': key, 'valueFrom': ref})
                added.append(key)
        plans.append({'service': name, 'current_arn': service['taskDefinition'],
                      'desired_count': service['desiredCount'], 'original': registration(current),
                      'proposed': copy.deepcopy(proposed), 'added_names': added})
    return {'cluster': cluster, 'account': expected_account, 'services': plans}


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
    try:
        client = AwsCli(args.region)
        plan = build_plan(client, args.cluster, args.expected_account)
        result = apply_plan(client, plan, args.expected_plan, args.backup_dir) if args.apply else public_plan(plan)
        print(json.dumps(result, indent=2))
    except (ConfigurationError, ValueError, KeyError) as error:
        print(json.dumps({'error': str(error) if isinstance(error, ConfigurationError) else type(error).__name__}))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
