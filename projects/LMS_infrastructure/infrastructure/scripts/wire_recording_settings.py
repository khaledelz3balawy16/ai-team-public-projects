"""Plan or apply existing recording secret bindings, without changing their values.

Both upload-owner switches must remain off until reviewed code is deployed and
the overlapping VPS uploader is drained. This tool never enables a switch.
"""
import argparse
import copy
import json

from wire_live_bunny_settings import (
    AwsCli, ConfigurationError, apply_plan, public_plan, registration,
    service_definition,
)

LIVE = ('BUNNY_LIVE_STREAM_LIBRARY_ID', 'BUNNY_LIVE_STREAM_API_KEY',
        'BUNNY_LIVE_STREAM_TOKEN_KEY')
COACH = ('BUNNY_COACH_STREAM_LIBRARY_ID', 'BUNNY_COACH_STREAM_API_KEY',
         'BUNNY_COACH_STREAM_TOKEN_KEY')
LIVE_FLAGS = ('BUNNY_LIVE_RECORDING_UPLOADS_ENABLED', 'BUNNY_RECORDING_DIRECT_FETCH_ENABLED')
COACH_FLAGS = ('BUNNY_COACH_RECORDING_UPLOADS_ENABLED',)
TARGETS = {
    'curriculum-api': LIVE + LIVE_FLAGS,
    'learner-api': LIVE,
    'coach-api': COACH + COACH_FLAGS,
    'session-worker': LIVE + COACH + LIVE_FLAGS + COACH_FLAGS,
    'night-api': LIVE + COACH + LIVE_FLAGS + COACH_FLAGS,
}


def build_plan(client, cluster, expected_account, worker_cpu=None, worker_memory=None):
    if (worker_cpu, worker_memory) not in ((None, None), (512, 2048), (1024, 3072)):
        raise ConfigurationError('Use the measured 512/2048 profile or the previous 1024/3072 profile')
    if client('sts', 'get-caller-identity', {})['Account'] != expected_account:
        raise ConfigurationError('Unexpected AWS account')
    _, source = service_definition(client, cluster, 'curriculum-api')
    refs = [row['valueFrom'] for row in source['containerDefinitions'][0].get('secrets', [])
            if row['name'] == LIVE[0]]
    if len(refs) != 1:
        raise ConfigurationError('Missing authoritative LiveSessions secret binding')
    parts = refs[0].split(':')
    if len(parts) != 10 or parts[2] != 'secretsmanager' or parts[7:] != [LIVE[0], '', '']:
        raise ConfigurationError('Unexpected shared secret reference format')
    secret_id = ':'.join(parts[:7])
    values = json.loads(client('secretsmanager', 'CHANGE_ME', {'SecretId': secret_id})['SecretString'])
    required = LIVE + COACH + LIVE_FLAGS + COACH_FLAGS
    if any(not str(values.get(key, '')).strip() for key in required):
        raise ConfigurationError('Recording settings missing from the shared secret; values withheld')
    if (str(values[LIVE[0]]) != '796471' or not str(values[COACH[0]]).isdigit()
            or str(values[COACH[0]]) in ('796471', str(values.get('BUNNY_STREAM_LIBRARY_ID', '798153')))):
        raise ConfigurationError('Recording libraries must be separate from teaching materials')
    for key in LIVE_FLAGS + COACH_FLAGS:
        if str(values[key]).lower() not in ('true', 'false'):
            raise ConfigurationError('Recording switches require explicit true/false: ' + key)
    plans = []
    for name, keys in TARGETS.items():
        service, current = service_definition(client, cluster, name)
        deployments = service.get('deployments', [])
        if len(deployments) != 1 or deployments[0].get('rolloutState') != 'COMPLETED':
            raise ConfigurationError('Wait for the active release before wiring: ' + name)
        if name == 'session-worker':
            policy = service.get('deploymentConfiguration', {})
            if policy.get('minimumHealthyPercent') != 0 or policy.get('maximumPercent') != 100:
                raise ConfigurationError('Worker must stop before its replacement starts')
        proposed = registration(current)
        if name == 'session-worker' and worker_cpu is not None:
            proposed.update(cpu=str(worker_cpu), memory=str(worker_memory))
        container = proposed['containerDefinitions'][0]
        existing = {row['name']: row['valueFrom'] for row in container.get('secrets', [])}
        if not any(ref.startswith(secret_id + ':') for ref in existing.values()):
            raise ConfigurationError('Target does not already use the shared secret: ' + name)
        added = []
        for key in keys:
            ref = secret_id + ':' + key + '::'
            if any(row['name'] == key for row in container.get('environment', [])):
                raise ConfigurationError('Conflicting plain recording setting on ' + name + ': ' + key)
            if key in existing and existing[key] != ref:
                raise ConfigurationError('Conflicting recording secret on ' + name + ': ' + key)
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
    parser.add_argument('--worker-cpu', type=int)
    parser.add_argument('--worker-memory', type=int)
    args = parser.parse_args()
    if args.apply and not (args.expected_plan and args.backup_dir):
        parser.error('--apply requires --expected-plan and a private --backup-dir')
    try:
        client = AwsCli(args.region)
        plan = build_plan(client, args.cluster, args.expected_account, args.worker_cpu, args.worker_memory)
        result = apply_plan(client, plan, args.expected_plan, args.backup_dir) if args.apply else public_plan(plan)
        print(json.dumps(result, indent=2))
    except (ConfigurationError, ValueError, KeyError) as error:
        print(json.dumps({'error': str(error) if isinstance(error, ConfigurationError) else type(error).__name__}))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
