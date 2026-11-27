# LMS load test results (2): AWS with 3 workers per container

**Date:** 28 October 2026 (times are local, UTC+3)
**Follows:** `LOAD_TEST_RESULTS.md` (runs 1–4, same day)
**Tool:** k6, run from the same developer machine as runs 1–4
**Script:** `infrastructure/loadtest/lms.js` (wrapper: `run.sh`)
**Raw output:** `infrastructure/loadtest/results/lms-aws_kentbusinesscollege_net-20261028-155022.{txt,json}`, plus the task-count log `results/scaling-watch-run5.log`

## 1. Summary

With **3 Uvicorn worker processes per container** (1 vCPU / 2 GB per task, auto scaling at 60% CPU), AWS staging **held 200 users for 10 minutes and passed every threshold.** It was faster than both the earlier AWS runs and the VPS.

| | VPS (run 2) | AWS, 1 vCPU, 1 process (run 3) | **AWS, 1 vCPU, 3 workers + auto scaling (run 5)** |
|---|---|---|---|
| Result | ✅ Completed | ✅ Completed | ✅ **Completed** |
| Hold at 200 users | 3 min | 3 min | **10 min** |
| Failed requests | 0 / 41,278 | 1 / 30,248 | 2 / 105,422 (0.002%) |
| Requests per second | 105.1 | 76.8 | **129.2** |
| API, median | 0.42 s | 1.61 s | **0.36 s** |
| API, 95% under | 0.93 s | 2.17 s | **0.72 s** |
| API, 99% under | 1.50 s | 10.04 s | **1.33 s** |
| Page, 95% under | 0.48 s | 0.59 s | **0.43 s** |
| Sign-in service peak CPU (1-min average) | not collected | 46% (maximum) | **75%** |
| Auto scaling | n/a | n/a | ✅ **Scaled out 1 → 2 tasks** |

**Main findings**

1. **The workers fixed the bottleneck found in run 3.** Under Daphne, one process ran Django views one at a time, so a task levelled off at about 45% CPU while requests queued. With 3 workers the same task size used 75% CPU on average. The API median fell from 1.61 s to 0.36 s (about 4.5× faster), and throughput rose from 77 to 129 requests per second.
2. **AWS is now faster than the VPS on this test,** with a lower API median (0.36 s vs 0.42 s), a lower 95th percentile (0.72 s vs 0.93 s) and 23% more requests per second. See the fairness notes in section 3 before relying on the comparison.
3. **Auto scaling works.** CPU stayed above 60% for several minutes and the sign-in service scaled from 1 to 2 tasks at 16:00:18. The second task was serving traffic by 16:01:19.
4. **2 requests failed (HTTP 502/503 from the load balancer) at 16:01,** the minute the second task joined. Section 6 explains this.
5. **Memory is not a concern:** 3 workers use 47% of the 2 GB per task, flat for the whole run.

## 2. What changed since the first report

### 2.1 Changes for this run (3 workers per container)

| File | Change | Why |
|---|---|---|
| `backend/Dockerfile` | App server switched from **Daphne** to **Uvicorn 0.34.0** (`uvicorn[standard]`, installed in the image only) | Daphne cannot run several worker processes on one port; Uvicorn can (`--workers`). `[standard]` adds the WebSocket support chat needs. |
| `backend/Dockerfile` | New command: `uvicorn config.asgi:application --host 0.0.0.0 --port $PORT --workers $WEB_CONCURRENCY --proxy-headers --forwarded-allow-ips '*' --lifespan off` | `--workers` sets the number of processes. `--proxy-headers` keeps the real client IP from the load balancer (as Daphne's `--proxy-headers` did). `--lifespan off` is needed because the Channels router has no lifespan handler. |
| `backend/Dockerfile` | New `ENV WEB_CONCURRENCY=1` (local default) | ECS overrides it; a local `docker run` stays at one process. |
| `infrastructure/variables.tf` | New variable `web_workers` (default **3**) | One setting controls workers for all 9 services. |
| `infrastructure/ecs.tf` | `WEB_CONCURRENCY = var.web_workers` added to every container's environment | Passes the worker count to the containers and produces new task definition revisions. |

**Not changed:**
- **`backend/requirements.txt`.** Uvicorn is installed in the Dockerfile only, so the VPS and other developers keep Daphne exactly as before.
- **Django code.**
- **The production VPS.**

**Deployment record:**
- Image `lms-staging-backend:staging`, digest `sha256:7deb7c542a1a74ebbb152ed75aab4caed07dc1e4a0337e194abb5b5c635283c3`, built with `--provenance=false`.
- Terraform: 9 task definitions replaced and 9 services updated.
- **Correction (found after the 1,000-user runs): only 4 of the 9 services received the 3-worker revision:** `login-api:7`, `quiz-api:7`, `engagement-api:7` and `audit-api:7`.
  - The other 5 (`curriculum-api`, `coach-api`, `learner-api`, `chat`, `enrolment-api`) failed to start new tasks. ECS reported *"You've reached the limit on the number of vCPUs you can run concurrently"*: the account's Fargate quota is 12 vCPU, and 10 are in use (9 LMS tasks + 1 image-uploader task, 1 vCPU each).
  - The circuit breaker rolled these 5 back to their previous revision (`:6`), so they still run one process per container.
  - **Run 5 is unaffected:** it only loaded `login-api`, which was confirmed running 3 workers (3 `Started server process` lines in its logs).
  - Another `:7` service was spot-checked before the run and reported as `chat:6`. That was a mistake: `chat:6` is the rolled-back revision.
- Checks after deployment:
  - CloudWatch logs show 3 `Started server process` lines per container;
  - `/login_api/health/` → 200, `/curriculum_api/` → 401 (signed out, expected), `/` → 200.
- Local smoke test before pushing: 3 worker processes started and `/health/` → 200.

### 2.2 Earlier changes during the same session (already live before run 5)

| Change | Files | Detail |
|---|---|---|
| Task size 0.25 vCPU / 1 GB → **1 vCPU / 2 GB** | `variables.tf` (`task_cpu = 1024`, `task_memory = 2048`) | Made after run 1, where the sign-in task hit 100% CPU. |
| **Auto scaling** added | `autoscaling.tf` (new); `variables.tf` (`max_count = 4`, `cpu_target = 60`); `ecs.tf` (`lifecycle { ignore_changes = [desired_count] }`) | Target tracking on `ECSServiceAverageCPUUtilization` at 60%, 1–4 tasks per service. Scale-out cooldown 60 s, scale-in cooldown 300 s. `desired_count = 0` still stops everything. |
| Sign-in and email URLs point at the AWS site | `ecs.tf` | `FRONTEND_URL`, `MICROSOFT_SSO_CALLBACK_URI`, `AZURE_LOGIN_APP_REDIRECT_URI`, `MICROSOFT_CALLBACK_URI` and `GOOGLE_CALLBACK_URI` set to `https://lms-aws.kentbusinesscollege.net/...` instead of the `localhost` values in `backend/.env`. |
| Configurable hold time in the test | `loadtest/lms.js` | `HOLD` environment variable (default `3m`), so auto scaling has time to react. Run 5 used `HOLD=10m`. |

## 3. Limits and fairness of the comparison

- **Same test as before:** an **admin (staff)** account, so each virtual user called only `GET /login_api/me/` plus the page `GET /learner/home`. The heavier learner API calls were **not** tested, and database load was light.
- **One shared session.** All virtual users shared one sign-in, so sign-in itself was not load-tested.
- **Not identical conditions with the VPS.**
  - The VPS (run 2) ran at 14:11 with a 3-minute hold; run 5 ran at 15:50 with a 10-minute hold.
  - Live learner traffic on the VPS was different at the two times.
  - The VPS's server-side metrics were not collected.
- **One test machine.** Run 4 earlier showed that this machine's connection can become the bottleneck. In run 5 the client network was healthy: connection and TLS times were 0 ms up to the 99th percentile, and the load balancer's figures match k6's.
- **Shared production database.** Both sites use it, so database-heavy tests should run out of hours.

## 4. Test design (unchanged except the hold time)

| Item | Value |
|---|---|
| Virtual users | Ramp 0 → 50 (1 min) → 200 (2 min), **hold 200 for 10 min**, ramp down (30 s) |
| Each iteration | 1 page request (`GET /learner/home`) + 1 API request (`GET /login_api/me/`), then 1–3 s of think time |
| Authentication | One sign-in in `setup()`, shared `kbc_session` cookie, signed out in `teardown()` |
| Abort limits | Failed requests ≥ 5%, or API p95 ≥ 5 s (both assessed after 30 s) |
| Report-only targets | Page p95 < 1 s; checks > 95% |
| Command | `HOLD=10m BASE_URL=https://lms-aws.kentbusinesscollege.net ./run.sh` |

## 5. Run 5 detailed results

- **Time:** 15:50:22 – about 16:04 (13 min 40 s)
- **Result:** ✅ Completed. All thresholds passed.

### 5.1 Client side (k6)

All durations are in milliseconds.

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 325 | 296 | 567 | 633 | 1,195 | 11,932 |
| API (`/login_api/me/`) | 461 | 362 | 614 | 723 | 1,327 | 11,932 |
| Page (`/learner/home`) | 189 | 117 | 373 | 430 | 971 | 3,536 |
| Server wait (TTFB) | 324 | 295 | 565 | 629 | 1,161 | 11,932 |
| TCP connect | 0.1 | 0 | 0 | 0 | 0 | 1,068 |
| TLS handshake | 0.2 | 0 | 0 | 0 | 0 | 1,328 |
| Blocked (waiting for a connection) | 0.3 | 0 | 0 | 0 | 0 | 1,570 |

| Totals | |
|---|---|
| Requests | 105,422 (129.2/s) |
| Failed | 2 (0.002%), both API requests |
| Checks passed | 105,418 / 105,420 (`page 200`: all passed; `api 200`: 52,708 / 52,710) |
| Iterations | 52,710 (64.6/s) |
| Peak virtual users | 200 |
| Data received / sent | 522 MB / 6.9 MB |

### 5.2 Server side: sign-in service (`login-api`)

CPU per minute (average across tasks / highest task):

| 15:50 | 15:51 | 15:52 | 15:53 | 15:54 | 15:55 | 15:56 | 15:57 | 15:58 | 15:59 | 16:00 | 16:01 | 16:02 | 16:03 | 16:04 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 / 19 | 6 / 17 | 33 / 45 | 55 / 62 | 57 / 59 | 68 / 70 | 65 / 75 | 73 / 76 | **75 / 81** | 71 / 74 | 36 / 76 | 49 / **93** | 34 / 36 | 31 / 38 | 1 / 3 |

- **Memory:** 47% of 2 GB (about 960 MB with 3 workers), flat for the whole run.
- **Task count (desired/running):**

| Time | Tasks |
|---|---|
| 15:50:22 | 1 / 1 |
| 16:00:18 | Auto scaling: "Setting desired count to 2", successful |
| 16:00:31 | 2 / 1 (new task starting) |
| 16:01:19 | 2 / 2 (new task serving) |

The other 8 services stayed at 1 task, because the test only loaded the sign-in service.

### 5.3 Server side: load balancer

| Minute | Requests | Task response time p95 | p99 |
|---|---|---|---|
| 15:50 | 173 | 0.22 s | 2.28 s |
| 15:51 | 1,182 | 0.21 s | 0.27 s |
| 15:52 | 2,689 | 0.22 s | 0.40 s |
| 15:53 | 3,997 | 0.45 s | 0.87 s |
| 15:54 | 4,138 | 0.32 s | 0.57 s |
| 15:55 | 4,291 | 0.45 s | 0.81 s |
| 15:56 | 4,545 | 0.46 s | 0.99 s |
| 15:57 | 4,612 | 0.62 s | 1.03 s |
| 15:58 | 4,933 | 0.34 s | 0.63 s |
| 15:59 | 4,632 | 0.38 s | 0.72 s |
| 16:00 | 4,765 | 0.68 s | 1.02 s |
| 16:01 | 4,329 | 0.47 s | **10.46 s** |
| 16:02 | 4,974 | 0.21 s | 0.24 s |
| 16:03 | 3,482 | 0.21 s | 0.31 s |

| Error counts (whole run) | |
|---|---|
| 5xx returned by the tasks | 0 |
| 5xx returned by the load balancer | **2** |
| 4xx returned by the tasks | 1 (not one of the test's checked requests; cause not recorded without access logs) |

## 6. Analysis

### Why the workers helped

Daphne runs ordinary (synchronous) Django views in a single worker thread per process. In run 3, one 1 vCPU task could therefore do only about half a CPU's work, and extra requests waited in a queue. CPU levelled off at about 45%, yet the API median was 1.6 s.

With 3 Uvicorn processes, three views run in parallel in each task:
- CPU rose to 70–80%, so the vCPU is now actually used;
- queueing almost disappeared (API median 0.36 s);
- the same 1 vCPU task handled about 70% more requests per second.

### Why auto scaling now triggers

The 60% CPU target was unreachable with one process (CPU peaked at 46%). With 3 workers, average CPU passed 60% at 15:53 and stayed there. Target tracking needs a few minutes of sustained readings before it acts, so it added the second task at 16:00:18. It started serving at 16:01:19, and CPU per task then dropped to 31–36%.

### The 2 failed requests

Both failures were load-balancer 5xx responses (the tasks themselves returned no 5xx), in the minute 16:00–16:01, when the second task was being added. In the same minute the p99 response time jumped to 10.5 s, with the highest single task at 93% CPU. The most likely cause: brief overload while the new task started and joined the target group. This is not confirmed: the load balancer's access logs are not enabled, so the exact status codes and targets are not recorded.

Possible mitigations, not applied:
- scale out earlier, with a lower target such as 50%, or with step scaling on a 1-minute alarm;
- run at least 2 tasks of the busiest services, so a new task is never joining a single saturated one;
- set a load-balancer slow-start period so a new task receives traffic gradually.

### Is 3 workers the right number?

For a 1 vCPU / 2 GB task, 3 workers used 75% CPU and 47% memory under this load, which leaves headroom on both. More workers would mostly compete for the same vCPU. The better ways to grow are more tasks (auto scaling) or a larger task (2 vCPU with 4–5 workers). Request-heavy, database-light endpoints such as `/login_api/me/` favour more workers; database-heavy learner pages spend more time waiting on queries and may benefit from more.

## 7. Recommendations

1. **Keep 3 workers per container** for 1 vCPU tasks.
2. **Re-test with a learner account.** This run, like the others, only exercised `/login_api/me/`. The learner home calls (dashboard, training plan, my learning, lectures) involve far more database work and may behave differently.
3. **Smooth the scale-out:** consider a minimum of 2 tasks for `login-api` and `learner-api`, a load-balancer slow-start period, or a slightly lower CPU target. Then re-check that scaling causes no errors.
4. **Enable load-balancer access logs** (to S3) for future tests, so any 5xx can be traced to its exact cause.
5. **Re-run the VPS with the 10-minute hold**, ideally collecting its CPU and memory, for a like-for-like comparison.
6. **Run the load generator inside AWS** for tests above 200 users. This machine's connection limited run 4.
7. **Before using this setup for production,** review chat (WebSocket) behaviour with multiple workers in a live test. Channels uses Valkey, so messages are shared across processes and tasks, but chat was not exercised by this load test.

## 8. Current AWS configuration

| Setting | Value |
|---|---|
| App server | Uvicorn 0.34.0, **3 workers** per container (`web_workers`) |
| Task size | 1 vCPU / 2 GB |
| Tasks per service | 1 minimum, 4 maximum |
| Auto scaling | 60% average CPU target; scale-out cooldown 60 s, scale-in cooldown 300 s |
| `login-api` after the test | 2 tasks; auto scaling returns it to 1 once CPU stays low |
| Approximate cost | About $12/day for 9 tasks at 1 vCPU, plus about $1.30/day for each extra task while scaled out |
| Stop when idle | `terraform apply -var desired_count=0` |

## 9. How to repeat

```bash
cd infrastructure/loadtest
# Account in infrastructure/loadtest.env (git-ignored): LOADTEST_EMAIL=..., LOADTEST_PASSWORD=...
HOLD=10m BASE_URL=https://lms-aws.kentbusinesscollege.net ./run.sh   # this run
HOLD=10m BASE_URL=https://lms.kentbusinesscollege.org ./run.sh       # VPS, like for like
```

Run one site at a time: both use the same production database.
