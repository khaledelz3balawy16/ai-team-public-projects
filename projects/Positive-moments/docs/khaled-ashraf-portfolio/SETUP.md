# Setup

Start from the sanitized original README when available. The entries below are extracted from this specific source snapshot.

## Environment

Supply your own development or sandbox service configuration. Environment templates contain placeholder values. Runtime credentials and production data are excluded.

- `backend/.env.example`
- `deploy/publisher.env.template`
- `deploy/qa-core.env.template`
- `frontend/.env.example`
- `services/kbc-media-worker/.env.example`

## JavaScript / TypeScript

### `frontend`

Package manager metadata: `not specified`.

| Existing script | Command in manifest |
| --- | --- |
| `npm run dev` | `vite` |
| `npm run build` | `vue-tsc -b && vite build` |
| `npm run lint` | `eslint . --max-warnings=0` |
| `npm run test` | `vitest run` |

### `services/kbc-media-worker`

Package manager metadata: `not specified`.

| Existing script | Command in manifest |
| --- | --- |
| `npm run start` | `node src/worker.js` |


## Python requirement files

- `automation/scheduler/requirements.txt`
- `backend/requirements.txt`
- `requirements-dev.txt`

## External integrations

Consult the source configuration for databases, identity providers, email, storage, payments, and other APIs. Select local or sandbox targets before running startup hooks, migrations, seeds, or integration tests. No external-service credentials are provided in this copy.
