# LMS load test results: VPS vs AWS staging

**Date:** 28 October 2026 (times are local, UTC+3)
**Tool:** k6, run from one developer machine
**Script:** `infrastructure/loadtest/lms.js` (wrapper: `run.sh`)
**Raw output:** `infrastructure/loadtest/results/` (k6 text summary and JSON export for each run)

## 1. Summary

| | VPS | AWS, 0.25 vCPU | AWS, 1 vCPU | AWS, 1 vCPU + auto scaling |
|---|---|---|---|---|
| Run | 2 | 1 | 3 | 4 |
| Result | ✅ Completed | ⚠️ Stopped at 142 users | ✅ Completed | ❌ Not valid (client network) |
| Peak users held | 200 | 142 | 200 | 200, for under a minute |
| Failed requests | 0 / 41,278 | 0 / 4,062 | 1 / 30,248 | 0 / 8,354 |
| Requests per second | **105.1** | 29.2 | 76.8 | 39.6 |
| API, median | **0.42 s** | 1.71 s | 1.61 s | 0.45 s |
| API, 95% under | **0.93 s** | 5.09 s | 2.17 s | 5.22 s |
| Page, 95% under | 0.48 s | **0.19 s** | 0.59 s | 10.0 s |

**Main findings**

1. **The VPS handled 200 users comfortably:** no errors, and 95% of API calls finished in under 1 second.
2. **AWS at its original size (0.25 vCPU per task) could not reach 200 users.** The sign-in service's CPU reached 100% at about 142 users, and the safety limit stopped the test.
3. **AWS at 1 vCPU per task held 200 users,** with 1 error in about 30,000 requests. It was still about 2× slower than the VPS on API calls. CPU peaked at only 46%, so CPU size was no longer the limit (section 6).
4. **The page (static React app) loads faster on AWS** through CloudFront when the client's network is not saturated: 0.19 s vs 0.48 s at the 95th percentile.
5. **The auto-scaling run (run 4) does not measure AWS.** The load balancer shows the servers answering in under 1 second. The delays of 5–49 s happened between the test machine and the internet. Auto scaling never triggered: CPU peaked at 32% against a 60% target.

## 2. Important limits of these results

- **Only one API endpoint was tested.** The test account is an **admin (staff)** account, not a learner. Each virtual user therefore called only `GET /login_api/me/` plus the page `/learner/home`. The heavier learner API calls (dashboard header, training plan, my learning, lectures) were not tested. The script runs them automatically when it is given a learner account.
- **One shared session.** The script signs in once and all virtual users share that session. This avoids 200 sign-in records in the production database and protects the test account from lockout. Sign-in itself was therefore **not** load-tested.
- **Both sites use the production database.** Database load was light in these runs (one small query per API call). With a learner account it would be much heavier.
- **One test machine.** All traffic came from one computer and one internet connection. Run 4 shows this connection can become the bottleneck at 200 users. Results from runs 1–3 may also include some client-side delay.
- **Real learners were using the VPS** during run 2. Their traffic is mixed into the VPS figures.
- **Only GET requests** were made. Nothing was written to the database apart from session activity.

## 3. Test design

| Item | Value |
|---|---|
| Virtual users | Ramp 0 → 50 (1 min) → 200 (2 min), hold 200 (3 min; 10 min in run 4), ramp down (30 s) |
| Each iteration | 1 page request (`GET /learner/home`) + 1 API request (`GET /login_api/me/`), then 1–3 s of think time |
| Authentication | One sign-in in `setup()`, `kbc_session` cookie shared by every user, signed out in `teardown()` |
| CSRF header | `X-Requested-With: XMLHttpRequest`, as the frontend sends |
| User agent | `kbc-lms-loadtest/1.0 (k6)`, so the traffic can be identified in logs |

**Automatic abort limits** (to protect live learners):

| Metric | Limit | Action |
|---|---|---|
| Failed requests | ≥ 5% | Abort, assessed after 30 s |
| API 95th-percentile duration | ≥ 5 s | Abort, assessed after 30 s |
| Page 95th-percentile duration | ≥ 1 s | Report only |
| Checks passed | ≤ 95% | Report only |

## 4. Environments

| | VPS (production) | AWS staging |
|---|---|---|
| URL | `https://lms.kentbusinesscollege.org` | `https://lms-aws.kentbusinesscollege.net` |
| Page served by | VPS web server | CloudFront → S3 |
| API served by | VPS processes behind the proxy | CloudFront → ALB → ECS Fargate (one service per API, 9 services) |
| App server | Django | Django on Daphne (ASGI), one process per task |
| Database | Production | **Same production database** |
| Region | VPS location | eu-north-1 (Stockholm) |

AWS task size by run:

| Run | CPU / memory per task | Tasks per service | Auto scaling |
|---|---|---|---|
| 1 | 0.25 vCPU / 1 GB | 1 | None |
| 3 | 1 vCPU / 2 GB | 1 | None |
| 4 | 1 vCPU / 2 GB | 1 (min) – 4 (max) | Target tracking, 60% average CPU, scale-out cooldown 60 s, scale-in cooldown 300 s |

## 5. Detailed results per run

All durations are in milliseconds unless stated.

### Run 1: AWS, 0.25 vCPU per task

- **Time:** 14:09:10 – 14:11:30 (2 min 20 s)
- **Result:** ⚠️ Aborted. API 95th percentile was 5,085 ms, over the 5 s limit, at 142 users.

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 1,064 | 250 | 3,815 | 4,480 | 5,665 | 6,197 |
| API (`/login_api/me/`) | 2,093 | 1,707 | 4,493 | 5,085 | 5,969 | 6,197 |
| Page (`/learner/home`) | 81 | 53 | 166 | 191 | 383 | 1,605 |
| Server wait (TTFB) | 1,063 | 250 | 3,813 | 4,475 | 5,665 | 6,187 |
| TCP connect | 1.8 | 0 | 0 | 0 | 48 | 193 |
| TLS handshake | 2.0 | 0 | 0 | 0 | 56 | 170 |

| Totals | |
|---|---|
| Requests | 4,062 (29.2/s) |
| Failed | 0 (0.00%) |
| Checks passed | 4,060 / 4,060 |
| Iterations | 1,936 (13.9/s) |
| Peak virtual users | 142 |
| Data received / sent | 21.3 MB / 0.53 MB |

Sign-in service (`login-api`) CPU, maximum per minute:

| 14:09 | 14:10 | 14:11 |
|---|---|---|
| 55% | **100%** | **100%** |

### Run 2: VPS

- **Time:** 14:11:46 – 14:18:20 (about 6 min 30 s)
- **Result:** ✅ Completed. All thresholds passed.

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 349 | 342 | 603 | 787 | 1,367 | 3,521 |
| API (`/login_api/me/`) | 433 | 418 | 721 | 929 | 1,495 | 3,521 |
| Page (`/learner/home`) | 265 | 274 | 416 | 482 | 1,002 | 3,139 |
| Server wait (TTFB) | 349 | 342 | 603 | 787 | 1,367 | 3,521 |
| TCP connect | 0.5 | 0 | 0 | 0 | 0 | 780 |
| TLS handshake | 0.7 | 0 | 0 | 0 | 0 | 4,468 |

| Totals | |
|---|---|
| Requests | 41,278 (105.1/s) |
| Failed | 0 (0.00%) |
| Checks passed | 41,276 / 41,276 |
| Iterations | 20,638 (52.5/s) |
| Peak virtual users | 200 |
| Data received / sent | 189.7 MB / 2.9 MB |

VPS server metrics (CPU, memory, database) were not collected.

### Run 3: AWS, 1 vCPU per task

- **Time:** 14:28:55 – 14:35:30 (about 6 min 30 s)
- **Result:** ✅ Completed. All thresholds passed.

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 839 | 300 | 1,929 | 2,046 | 5,465 | 18,783 |
| API (`/login_api/me/`) | 1,471 | 1,608 | 2,016 | 2,169 | 10,035 | 18,783 |
| Page (`/learner/home`) | 207 | 73 | 345 | 587 | 3,127 | 10,145 |
| Server wait (TTFB) | 835 | 300 | 1,919 | 2,028 | 5,465 | 18,783 |
| TCP connect | 0.7 | 0 | 0 | 0 | 0 | 1,074 |
| TLS handshake | 0.8 | 0 | 0 | 0 | 0 | 5,027 |

| Totals | |
|---|---|
| Requests | 30,248 (76.8/s) |
| Failed | 1 (0.003%): one page request timed out |
| Checks passed | 30,245 / 30,246 |
| Iterations | 15,123 (38.4/s) |
| Peak virtual users | 200 |
| Data received / sent | 150.6 MB / 2.2 MB |

Sign-in service (`login-api`) CPU, maximum per minute:

| 14:29 | 14:30 | 14:31 | 14:32 | 14:33 |
|---|---|---|---|---|
| 22% | 33% | 45% | 46% | 44% |

### Run 4: AWS, 1 vCPU per task + auto scaling (not valid)

- **Time:** 14:56:20 – 14:59:52 (3 min 32 s)
- **Result:** ❌ Aborted. API p95 was 5,224 ms and page p95 was 10,002 ms.
- **Not valid as a measurement of AWS:** see the comparison with server-side timings below.

| Metric (k6, client side) | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 1,113 | 289 | 1,271 | 7,112 | 16,422 | 49,586 |
| API (`/login_api/me/`) | 1,159 | 449 | 1,272 | 5,224 | 13,149 | 24,826 |
| Page (`/learner/home`) | 1,067 | 82 | 1,270 | 10,002 | 22,245 | 49,586 |
| TCP connect | 13.5 | 0 | 0 | 0 | 53 | 13,518 |
| TLS handshake | 11.7 | 0 | 0 | 0 | 62 | 11,833 |
| Blocked (waiting for a connection) | 25.3 | 0 | 0 | 0 | 121 | 23,106 |

| Totals | |
|---|---|
| Requests | 8,354 (39.6/s) |
| Failed | 0 (0.00%) |
| Checks passed | 8,352 / 8,352 |
| Iterations | 4,125 (19.6/s) |
| Peak virtual users | 200 |
| Data received / sent | 42.7 MB / 0.9 MB |

**Server side: AWS load balancer, response time of the tasks:**

| Minute | Requests at the ALB | p95 | p99 |
|---|---|---|---|
| 14:56 | 261 | 0.21 s | 0.34 s |
| 14:57 | 1,555 | 0.33 s | 0.38 s |
| 14:58 | 2,169 | 0.94 s | 1.07 s |
| 14:59 | **229** | 0.21 s | 0.38 s |

Sign-in service CPU (average per minute): 14:57 **16%**, 14:58 **32%**, 14:59 7%.
Task count (desired/running) stayed at **1/1** throughout. No scaling activity was recorded.

**Why the run is not valid:**

- The servers answered within 1 s at the 95th percentile, while k6 measured up to 49 s.
- The page is served by CloudFront and never reaches the servers, yet it slowed to 10 s at the 95th percentile.
- Requests arriving at the load balancer fell from 2,169 to 229 per minute while 200 users were active.
- Connect, TLS and blocked times rose to 11–23 s.

All of this points to the test machine's internet connection, not to AWS.

## 6. Analysis

### Why AWS was slower than the VPS on API calls

- **Run 1 (0.25 vCPU):** CPU-bound. The sign-in task sat at 100% CPU, requests queued, and latency rose until the abort limit.
- **Run 3 (1 vCPU):** **not** CPU-bound. CPU peaked at 46%, yet the API median was 1.6 s against 0.42 s on the VPS. Two likely causes, not yet confirmed by measurement:
  1. **One Django process per task.** Daphne (ASGI) runs ordinary synchronous Django views one at a time in a single worker thread. One task can therefore use only about half of one vCPU however large it is, and extra requests wait in a queue. This matches the CPU levelling off at about 45%.
  2. **Distance to the database.** AWS runs in Stockholm and every API call queries the production database. If the database is closer to the VPS, each query takes longer from AWS.

### Why auto scaling did not trigger

The target is 60% average CPU, but a task under this process model levels off at about 45–50%, and reached only 32% in run 4. **With the current container setup, a 60% target is unlikely ever to trigger.**

### Page delivery

When the client network was not the bottleneck (run 1), CloudFront delivered `/learner/home` faster than the VPS: p95 191 ms vs 482 ms.

## 7. Recommendations

1. **Run the load generator inside AWS,** for example as a one-off ECS task, and test the VPS from the same place. This removes the client-network bottleneck seen in run 4 and makes the two sites directly comparable.
2. **Use several Django worker processes per container,** for example Gunicorn with Uvicorn workers, so a task can use its full vCPU. Alternatively, lower the auto-scaling target to about 40%. With multiple workers, the 60% target becomes reachable.
3. **Re-test with a learner account** so the real learner home API calls and the database load are included.
4. **Collect server-side metrics on the VPS** (CPU, memory, database time) during the next run, so both sites are compared on the same evidence.
5. **Measure database latency from each site** (for example, the time of `/login_api/health/`) to confirm or rule out distance to the database as a cause.
6. **Run out of hours.** Both sites share the production database, so heavier tests affect live learners.

## 8. Current AWS configuration (after these tests)

| Setting | Value |
|---|---|
| Task size | 1 vCPU / 2 GB (`task_cpu = 1024`, `task_memory = 2048`) |
| Tasks per service | 1 minimum, 4 maximum (`desired_count`, `max_count`) |
| Auto scaling | Target tracking on `ECSServiceAverageCPUUtilization` at 60% (`cpu_target`) |
| Approximate running cost | About $12/day with 9 tasks at 1 vCPU (more while scaled out) |
| Stop when idle | `terraform apply -var desired_count=0` |

## 9. How to repeat a run

```bash
# Account file (git-ignored, never printed):
#   infrastructure/loadtest.env with LOADTEST_EMAIL=... and LOADTEST_PASSWORD=...
cd infrastructure/loadtest
BASE_URL=https://lms-aws.kentbusinesscollege.net ./run.sh              # AWS
BASE_URL=https://lms.kentbusinesscollege.org ./run.sh                  # VPS
HOLD=10m PEAK_VUS=200 BASE_URL=https://lms-aws.kentbusinesscollege.net ./run.sh  # longer hold
```

Run one site at a time: both use the same production database.
