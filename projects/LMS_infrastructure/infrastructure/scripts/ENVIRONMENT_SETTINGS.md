# Local and production settings

Shared credentials should match the current AWS secret. Local front-end URLs,
OAuth callbacks, debug and cache choices stay local. Local allowed-host and CSRF
lists can include both local and deployed origins. `ecs.tf` independently sets
the deployed URLs, trusted hosts, debug flag, storage and cache endpoints; these
values override the same names in a developer's environment file.

When preparing Terraform variables, preserve a private, current production
reference instead of replacing all production settings with a development file:

```sh
python3 -I scripts/env_to_tfvars.py /private/local.env /private/secrets.tfvars \
  --production-env /private/current-production.env
```

The reference wins for existing settings and retains production-only keys.
New local names are included. Neither input is edited. Keep inputs, generated
variables, Terraform state, plans and operational backups outside Git. Review a
plan in the existing production workspace before applying Terraform. This
repository does not include that workspace's private state; do not create a new
empty production state and apply it over existing resources.

## Connect the existing LiveSessions settings

All Terraform services already use `local.app_secret_keys`, including the session
worker and night API. Services registered before a new key was added to the
shared JSON secret need their task definition updated to expose that key.

The following command is read-only by default and checks the expected account,
existing curriculum API secret references and both target definitions:

```sh
python3 -I scripts/wire_live_bunny_settings.py
```

Review the two added bindings and the printed plan fingerprint, then apply that
exact plan from reviewed main using a private backup folder:

```sh
python3 -I scripts/wire_live_bunny_settings.py --apply \
  --expected-plan REVIEWED_SHA256 --backup-dir /private/definition-backups
```

It copies only `BUNNY_LIVE_STREAM_LIBRARY_ID` and `BUNNY_LIVE_STREAM_API_KEY`
references already used by curriculum-api into session-worker and night-api.
It changes no secret value, image, command, role, resource size, desired count,
existing environment setting or night schedule. It refuses conflicting values
or a worker deployment that could overlap two workers, and restores previous
service definitions if a later update fails. Normal ECS deployment monitoring
is still required after the updates return. Re-running the plan after rollout
should report no additions. For a later Terraform apply, keep the two keys in
the existing production `app_secrets` input so the bindings remain present.

This reconnects the collection organizer. It does not change the original video
upload library or establish a single uploader across independent applications.

Synthetic verification (no AWS calls):

```sh
python3 -m unittest discover -s infrastructure/scripts -p 'test_*.py' -v
```

## Private live-session attachments

The application supports PDFs, PPT/PPTX and other allowed session attachments
in a private Bunny **Storage** zone. Use one primary region without replication
or a public Pull Zone. Supply `BUNNY_SESSION_ATTACHMENTS_ZONE`,
`BUNNY_SESSION_ATTACHMENTS_KEY` (the zone password, not a Stream/account key),
and `BUNNY_SESSION_ATTACHMENTS_HOST` through the existing private shared secret.
Keep the existing production `app_secrets` input in sync before a later Terraform
apply; `local.app_secret_keys` already exports these names without an IaC change.

From reviewed main, inspect the redacted plan:

```sh
python3 scripts/wire_session_attachment_settings.py
```

After reviewing its fingerprint, apply exactly that plan with the normal private
definition backup, then monitor ECS until the existing services are stable:

```sh
python3 scripts/wire_session_attachment_settings.py --apply \
  --expected-plan REVIEWED_SHA256 --backup-dir /private/definition-backups
```

Only curriculum-api, learner-api, session-worker and night-api gain the three
secret references. Images, roles, CPU/memory, schedules, desired counts and
existing settings are CHANGE_ME; the worker must stop before its replacement.
The same rollback safeguards apply. No files are migrated, and credentials for
saved files must remain available. Existing S3/Azure attachments retain their
original storage. Verify a synthetic file upload, retry, authorized download and
an unauthenticated storage denial before accepting the rollout. Never log keys.

This does **not** enable `SESSION_ATTACHMENTS_AUTO_IMPORT_ENABLED` or grant new
Microsoft permissions. Automated chat collection stays off until its separate
Microsoft consent requirement has been verified.
