# LMS load testing: VPS vs AWS staging (complete results)

**Period:** 28 October 2026, 14:09 – 29 October 2026, 11:56 (local time, UTC+3)
**Sites tested:**
- VPS (production): `https://lms.kentbusinesscollege.org`
- AWS staging: `https://lms-aws.kentbusinesscollege.net`

**Tool:** k6, run from one developer machine
**Script:** `infrastructure/loadtest/lms.js` (wrapper: `run.sh`)
**Raw output:** `infrastructure/loadtest/results/`: a k6 text summary and JSON export for each run, plus task-count logs (`scaling-watch*.log`)

This report covers every load test run in the period, and every AWS configuration change made between them. It supersedes `LOAD_TEST_RESULTS.md` and `LOAD_TEST_RESULTS_2.md`, which describe the first 5 runs in more depth.

---

## 1. Summary

### 1.1 All runs at a glance

| # | When | Site | Target users | AWS setup at the time | Result | Users reached | Req/s | API median | API p95 | Page p95 | Failed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 28 Oct 14:09 | AWS | 200 | 1 task × 0.25 vCPU, Daphne | ⚠️ Stopped (API slow) | 142 | 29.2 | 1.71 s | 5.09 s | 0.19 s | 0 |
| 2 | 28 Oct 14:11 | VPS | 200 | n/a | ✅ Completed | 200 | 105.1 | 0.42 s | 0.93 s | 0.48 s | 0 |
| 3 | 28 Oct 14:28 | AWS | 200 | 1 task × 1 vCPU, Daphne | ✅ Completed | 200 | 76.8 | 1.61 s | 2.17 s | 0.59 s | 1 |
| 4 | 28 Oct 14:56 | AWS | 200 (10 min) | + auto scaling at 60% | ❌ Invalid (client network) | 200 | 39.6 | 0.45 s | 5.22 s | 10.0 s | 0 |
| 5 | 28 Oct 15:50 | AWS | 200 (10 min) | + 3 Uvicorn workers (login-api) | ✅ Completed | 200 | **129.2** | **0.36 s** | **0.72 s** | 0.43 s | 2 |
| 6 | 28 Oct 16:15 | AWS | 1,000 | same as run 5 | ⏹ Stopped by request after ~1 min | n/a | n/a | n/a | n/a | n/a | n/a |
| 7a | 28 Oct 16:16 | VPS | 1,000 | n/a | ⚠️ Stopped (API slow) | 720 | 141.0 | 1.64 s | 5.10 s | 0.20 s | 0 |
| 7b | 28 Oct 16:20 | AWS | 1,000 | same as run 5; login-api scaled back to 1 task during the run | ⚠️ Stopped (API slow) | 669 | 139.4 | 1.47 s | 5.26 s | 0.61 s | 2 |
| 8a | 29 Oct 11:48 | VPS | 1,000 | n/a | ⚠️ Stopped (API slow) | 790 | 148.0 | 2.13 s | 5.26 s | 0.41 s | 0 |
| 8b | 29 Oct 11:53 | AWS | 1,000 | 2 tasks for 4 busy APIs, 3 workers everywhere, chat/audit removed | ⚠️ Stopped (API slow) | **818** | **218.3** | **0.43 s** | 5.05 s | 0.37 s | 1 |

"Stopped (API slow)" means the automatic safety limit ended the test: 95% of API calls were taking longer than 5 seconds. None of the runs stopped because of errors.

### 1.2 Main findings

1. **At 200 users, AWS now outperforms the VPS.** After the changes, AWS (run 5) had a lower API median (0.36 s vs 0.42 s), a lower 95th percentile (0.72 s vs 0.93 s) and 23% more requests per second than the VPS (run 2).
2. **Neither site holds 1,000 users at present.**
   - In the latest round, the VPS reached 790 users and AWS 818 before 95% of API calls passed 5 seconds.
   - AWS handled **47% more requests per second** than the VPS at its peak (218 vs 148). Its typical API call was about 5× faster (0.43 s vs 2.13 s).
3. **The biggest single improvement was running several worker processes per container.** Daphne serves ordinary Django views one at a time per process, which capped a 1 vCPU task at about 45% CPU. With 3 Uvicorn workers, the same task size used its full CPU and roughly doubled throughput.
4. **AWS is now capped by the account's Fargate quota of 12 vCPU, not by its design.**
   - The LMS uses 11 vCPU, so auto scaling can add only one more task.
   - Auto scaling also needs several minutes to react, while the 1,000-user tests ramp up in 3 minutes.
5. **Error rates stayed close to zero in every run** (at most 2 failed requests per run). Under overload, both sites slowed down rather than failing.

---

## 2. Important limits of these results

- **Only one API endpoint was tested.** The test account is an **admin (staff)** account. Each virtual user therefore loaded the page `GET /learner/home` and called only `GET /login_api/me/`. The heavier learner API calls (dashboard, training plan, my learning, lectures) were not tested. The script runs them automatically with a learner account.
- **Sign-in was not load-tested.** The script signs in once and all virtual users share that session. This avoids hundreds of sign-in records in the production database and protects the test account from lockout.
- **Both sites use the production database.** Database load in these tests was light: one small query per API call. A learner-account test would be much heavier.
- **One test machine and one internet connection.**
  - Run 4 shows this connection can become the bottleneck.
  - In the other runs, connection and TLS times stayed under about 100 ms for 99% of requests, so the client was not the limit.
- **No VPS server-side metrics** (CPU, memory, database) were collected. VPS results show *what* happened, not *why*.
- **Live learners were using the VPS** during the VPS runs, and their traffic is mixed into the VPS figures.
- **Conditions differ between runs:** time of day, hold time (3 or 10 minutes) and live traffic. Side-by-side comparisons are indicative, not exact.

---

## 3. Test design

### 3.1 What each virtual user does

| Step | Request | Notes |
|---|---|---|
| Once, before the test | `POST /login_api/login/` | One sign-in in `setup()`. The `kbc_session` cookie is shared by every virtual user. |
| Each iteration | `GET /learner/home` | The page: CloudFront/S3 on AWS, the VPS web server on the VPS |
| Each iteration | `GET /login_api/me/` | The API, with the session cookie and `X-Requested-With: XMLHttpRequest` |
| Each iteration | 1–3 s of think time | Random |
| Once, after the test | `POST /login_api/logout/` | Ends the shared session (not reached when a run is stopped manually) |

Requests are identified by the user agent `kbc-lms-loadtest/1.0 (k6)`.

### 3.2 Load profile

| Stage | 200-user runs | 1,000-user runs |
|---|---|---|
| Ramp 1 | 0 → 50 in 1 min | 0 → 250 in 1 min |
| Ramp 2 | → 200 in 2 min | → 1,000 in 2 min |
| Hold | 3 min (runs 1–3), 10 min (runs 4–5) | 10 min (planned) |
| Ramp down | 30 s | 30 s |

These are set by the `PEAK_VUS` and `HOLD` environment variables.

### 3.3 Automatic safety limits (to protect live learners)

| Metric | Limit | Action |
|---|---|---|
| Failed requests | ≥ 5% | **Abort**, assessed after 30 s |
| API 95th-percentile duration | ≥ 5 s | **Abort**, assessed after 30 s |
| Page 95th-percentile duration | ≥ 1 s | Report only |
| Checks passed | ≤ 95% | Report only |

### 3.4 Running order

Runs were made **one site at a time**, never both at once, because both sites share the production database. In rounds 7 and 8 the VPS ran first, then there was a 2-minute pause, then AWS.

---

## 4. AWS configuration timeline

### 4.1 State before testing

- **Services:** 9 ECS Fargate services, one per API, mirroring the VPS proxy. Ports 8001–8009: curriculum, coach, quiz, learner, engagement, audit, chat, enrolment, login.
- **Tasks:** 1 task per service, **0.25 vCPU / 1 GB**, Django on **Daphne** (one process).
- **Traffic path:** CloudFront serves the React app from S3 and sends API paths to the ALB, which routes them to the services.
- **Database:** the same production database as the VPS.

### 4.2 Changes, in order

| When | Change | Files | Reason | Before runs |
|---|---|---|---|---|
| 28 Oct ~14:20 | Task size 0.25 vCPU / 1 GB → **1 vCPU / 2 GB** for all services | `variables.tf` (`task_cpu`, `task_memory`) | Run 1: sign-in task at 100% CPU | 3 |
| 28 Oct ~14:40 | **Auto scaling** added: target tracking on average CPU, 60% target, 1–4 tasks per service, scale-out cooldown 60 s, scale-in cooldown 300 s | `autoscaling.tf` (new), `variables.tf` (`max_count`, `cpu_target`), `ecs.tf` (`ignore_changes = [desired_count]`) | Let busy services add tasks | 4 |
| 28 Oct ~14:40 | Test hold time made configurable | `loadtest/lms.js` (`HOLD`) | Give auto scaling time to react | 4 |
| 28 Oct ~15:40 | App server **Daphne → Uvicorn 0.34.0 with 3 workers** per container; Uvicorn installed in the image only, `requirements.txt` and the VPS unchanged | `backend/Dockerfile`; `variables.tf` (`web_workers = 3`); `ecs.tf` (`WEB_CONCURRENCY`) | Run 3: 1 vCPU task levelled off at ~45% CPU, with requests queuing behind a single process | 5 |
| 28 Oct ~15:45 | *Found later:* only 4 of 9 services (login, quiz, engagement, audit) received the 3-worker version. The other 5 hit the **12 vCPU Fargate quota** and rolled back automatically. | — | Account limit (10 of 12 vCPU were in use) | affects 5, 6, 7 |
| 28 Oct ~17:00 | **image-uploader stopped** (0 tasks; a separate application on the same account) | AWS CLI only; its own Terraform restores it | Free 1 vCPU | 8 |
| 28 Oct ~17:00 | **Per-service sizes:** chat → 0.25 vCPU / 1 GB / 1 worker; audit-api → 0.5 vCPU / 1 GB / 2 workers | `variables.tf` (`service_sizes`), `ecs.tf` | Make room under the quota | 8 |
| 28 Oct ~17:00 | **Minimum 2 tasks** for login, learner, curriculum and enrolment | `variables.tf` (`service_min_counts`), `autoscaling.tf` | Spikes shouldn't wait for auto scaling | 8 |
| 28 Oct ~17:20 | Services with 2+ tasks now update **one task at a time** (min 50%, max 100%), with AZ rebalancing off for them (AWS requires that combination) | `ecs.tf` | Updates need no spare vCPU under the quota | 8 |
| 29 Oct ~11:30 | **chat and audit-api removed** from AWS. Their URLs now go to curriculum-api, which runs the same Django app. | `variables.tf` (`disabled_services`), `ecs.tf`, `autoscaling.tf`, `alb.tf`, `outputs.tf` | Free vCPU, so coach-api could get its 3-worker update | 8 |
| 29 Oct ~11:35 | 3-worker version completed on **all remaining services** (coach was the last) | — | — | 8 |
| Not applied | `cpu_target` changed 60 → 50 in `variables.tf` (edited manually, pending `terraform apply`) | `variables.tf` | — | — |

### 4.3 AWS setup used in each run

| Run | login-api tasks | Size per task | Process model | Auto scaling | Other services |
|---|---|---|---|---|---|
| 1 | 1 | 0.25 vCPU / 1 GB | Daphne (1 process) | none | 8 × 1 task, same size |
| 3 | 1 | 1 vCPU / 2 GB | Daphne (1 process) | none | 8 × 1 task, same size |
| 4 | 1 (min) – 4 | 1 vCPU / 2 GB | Daphne (1 process) | 60% CPU | same |
| 5 | 1 → 2 during the run | 1 vCPU / 2 GB | **Uvicorn, 3 workers** | 60% CPU | 3 with 3 workers, 5 still on Daphne |
| 7b | 2 → **1** at 16:21 (scale-in left over from run 5) | 1 vCPU / 2 GB | Uvicorn, 3 workers | 60% CPU | same as run 5 |
| 8b | **2 (minimum)** | 1 vCPU / 2 GB | Uvicorn, 3 workers | 60% CPU; 1 vCPU spare | learner/curriculum/enrolment × 2; coach/quiz/engagement × 1; chat and audit removed |

---

## 5. Detailed results per run

All durations are in milliseconds unless stated. "TTFB" is time to first byte (server wait).

### Run 1: AWS, 200 users, 0.25 vCPU per task

- **Time:** 28 Oct 14:09:10 – 14:11:30 (2 min 20 s)
- **Result:** ⚠️ Aborted at 142 users: API p95 5,085 ms

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 1,064 | 250 | 3,815 | 4,480 | 5,665 | 6,197 |
| API | 2,093 | 1,707 | 4,493 | 5,085 | 5,969 | 6,197 |
| Page | 81 | 53 | 166 | 191 | 383 | 1,605 |
| TTFB | 1,063 | 250 | 3,813 | 4,475 | 5,665 | 6,187 |
| TCP connect | 1.8 | 0 | 0 | 0 | 48 | 193 |
| TLS handshake | 2.0 | 0 | 0 | 0 | 56 | 170 |

| Totals | |
|---|---|
| Requests | 4,062 (29.2/s) |
| Failed | 0 |
| Iterations | 1,936 (13.9/s) |
| Peak users | 142 |
| Data received / sent | 21.3 MB / 0.5 MB |
| login-api CPU (max per minute) | 14:09 55%, 14:10 **100%**, 14:11 **100%** |

**Conclusion:** CPU-bound. A single 0.25 vCPU task cannot serve this load.

### Run 2: VPS, 200 users

- **Time:** 28 Oct 14:11:46 – about 14:18:20
- **Result:** ✅ Completed. All thresholds passed.

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 349 | 342 | 603 | 787 | 1,367 | 3,521 |
| API | 433 | 418 | 721 | 929 | 1,495 | 3,521 |
| Page | 265 | 274 | 416 | 482 | 1,002 | 3,139 |
| TTFB | 349 | 342 | 603 | 787 | 1,367 | 3,521 |
| TCP connect | 0.5 | 0 | 0 | 0 | 0 | 780 |
| TLS handshake | 0.7 | 0 | 0 | 0 | 0 | 4,468 |

| Totals | |
|---|---|
| Requests | 41,278 (105.1/s) |
| Failed | 0 |
| Iterations | 20,638 (52.5/s) |
| Peak users | 200 |
| Data received / sent | 189.7 MB / 2.9 MB |

### Run 3: AWS, 200 users, 1 vCPU per task

- **Time:** 28 Oct 14:28:55 – about 14:35:30
- **Result:** ✅ Completed. All thresholds passed.

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 839 | 300 | 1,929 | 2,046 | 5,465 | 18,783 |
| API | 1,471 | 1,608 | 2,016 | 2,169 | 10,035 | 18,783 |
| Page | 207 | 73 | 345 | 587 | 3,127 | 10,145 |
| TTFB | 835 | 300 | 1,919 | 2,028 | 5,465 | 18,783 |
| TCP connect | 0.7 | 0 | 0 | 0 | 0 | 1,074 |
| TLS handshake | 0.8 | 0 | 0 | 0 | 0 | 5,027 |

| Totals | |
|---|---|
| Requests | 30,248 (76.8/s) |
| Failed | 1 (one page request timed out) |
| Iterations | 15,123 (38.4/s) |
| Peak users | 200 |
| Data received / sent | 150.6 MB / 2.2 MB |
| login-api CPU (max per minute) | 14:29 22%, 14:30 33%, 14:31 45%, 14:32 46%, 14:33 44% |

**Conclusion:** no longer CPU-bound (46% peak), yet the API median was 1.6 s. Requests queued behind Daphne's single process.

### Run 4: AWS, 200 users for 10 min, auto scaling at 60% (not valid)

- **Time:** 28 Oct 14:56:20 – 14:59:52 (3 min 32 s)
- **Result:** ❌ Aborted. API p95 5,224 ms, page p95 10,002 ms.
- **Note:** a first attempt at this run (from about 14:39) never started, because of a script path error, and is not counted.

| Metric (client side) | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 1,113 | 289 | 1,271 | 7,112 | 16,422 | 49,586 |
| API | 1,159 | 449 | 1,272 | 5,224 | 13,149 | 24,826 |
| Page | 1,067 | 82 | 1,270 | 10,002 | 22,245 | 49,586 |
| TCP connect | 13.5 | 0 | 0 | 0 | 53 | 13,518 |
| TLS handshake | 11.7 | 0 | 0 | 0 | 62 | 11,833 |
| Blocked | 25.3 | 0 | 0 | 0 | 121 | 23,106 |

Server side, at the AWS load balancer:

| Minute | Requests | Task p95 | Task p99 |
|---|---|---|---|
| 14:56 | 261 | 0.21 s | 0.34 s |
| 14:57 | 1,555 | 0.33 s | 0.38 s |
| 14:58 | 2,169 | 0.94 s | 1.07 s |
| 14:59 | **229** | 0.21 s | 0.38 s |

| Totals | |
|---|---|
| Requests | 8,354 (39.6/s) |
| Failed | 0 |
| Iterations | 4,125 (19.6/s) |
| login-api CPU (average) | 16% / 32% / 7% |
| Tasks | 1 throughout (no scaling) |

**Why the run is not valid:**
- The servers answered within 1 s, while k6 waited up to 49 s.
- The page, which CloudFront serves without the servers, also slowed to 10 s.
- Requests arriving at the load balancer collapsed from 2,169 to 229 per minute.

All of this points to the test machine's internet connection. CPU also never reached the 60% target, because one Daphne process caps at about 45–50%.

### Run 5: AWS, 200 users for 10 min, 3 Uvicorn workers

- **Time:** 28 Oct 15:50:22 – about 16:04 (13 min 40 s)
- **Result:** ✅ Completed. All thresholds passed.

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 325 | 296 | 567 | 633 | 1,195 | 11,932 |
| API | 461 | 362 | 614 | 723 | 1,327 | 11,932 |
| Page | 189 | 117 | 373 | 430 | 971 | 3,536 |
| TTFB | 324 | 295 | 565 | 629 | 1,161 | 11,932 |
| TCP connect | 0.1 | 0 | 0 | 0 | 0 | 1,068 |
| TLS handshake | 0.2 | 0 | 0 | 0 | 0 | 1,328 |

| Totals | |
|---|---|
| Requests | 105,422 (129.2/s) |
| Failed | 2 (load-balancer 5xx at 16:01, while the second task joined) |
| Iterations | 52,710 (64.6/s) |
| Peak users | 200 |
| Data received / sent | 522 MB / 6.9 MB |
| Memory | 47% of 2 GB, flat |

login-api CPU per minute (average / highest task):

| 15:52 | 15:53 | 15:54 | 15:55 | 15:56 | 15:57 | 15:58 | 15:59 | 16:00 | 16:01 | 16:02 |
|---|---|---|---|---|---|---|---|---|---|---|
| 33/45 | 55/62 | 57/59 | 68/70 | 65/75 | 73/76 | **75/81** | 71/74 | 36/76 | 49/**93** | 34/36 |

**Auto scaling:** "Setting desired count to 2" at 16:00:18. The second task was serving by 16:01:19, after which CPU per task fell to 31–36%.

**Conclusion:** the workers removed the queueing. The API median fell from 1.61 s to 0.36 s, and the 60% scaling target became reachable.

### Run 6: AWS, 1,000 users (stopped on request)

- **Time:** 28 Oct 16:15:22, stopped after about 1 minute at the user's request, to run both sites instead
- **Result:** no summary recorded. The sign-out step did not run, so the shared test session stayed open until it expired.

### Run 7a: VPS, 1,000 users

- **Time:** 28 Oct 16:16:28 – 16:18:50 (2 min 22 s)
- **Result:** ⚠️ Aborted at 720 users: API p95 5,097 ms

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 1,166 | 155 | 4,209 | 4,739 | 5,437 | 5,689 |
| API | 2,268 | 1,641 | 4,748 | 5,097 | 5,530 | 5,689 |
| Page | 120 | 82 | 159 | 205 | 780 | 4,943 |
| TTFB | 1,166 | 155 | 4,209 | 4,738 | 5,437 | 5,689 |
| TCP connect | 4 | 0 | 0 | 0 | 83 | 2,245 |
| TLS handshake | 4 | 0 | 0 | 0 | 95 | 2,512 |
| Blocked | 8 | 0 | 0 | 0 | 181 | 2,827 |

| Totals | |
|---|---|
| Requests | 19,933 (141.0/s) |
| Failed | 0 |
| Iterations | 9,517 (67.3/s) |
| Peak users | 720 |
| Data received / sent | 96.1 MB / 2.6 MB |

### Run 7b: AWS, 1,000 users

- **Time:** 28 Oct 16:20:50 – 16:23:02 (2 min 12 s)
- **Result:** ⚠️ Aborted at 669 users: API p95 5,262 ms

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 1,061 | 302 | 3,630 | 4,359 | 5,692 | 7,171 |
| API | 1,978 | 1,474 | 4,384 | 5,262 | 5,912 | 7,171 |
| Page | 189 | 85 | 441 | 612 | 1,298 | 6,499 |
| TTFB | 1,049 | 301 | 3,627 | 4,358 | 5,692 | 7,171 |
| TCP connect | 4 | 0 | 0 | 0 | 78 | 2,105 |
| TLS handshake | 5 | 0 | 0 | 0 | 92 | 4,521 |
| Blocked | 10 | 0 | 0 | 0 | 180 | 4,772 |

| Totals | |
|---|---|
| Requests | 18,251 (139.4/s) |
| Failed | 2 |
| Iterations | 8,688 (66.4/s) |
| Peak users | 669 |
| Data received / sent | 95.7 MB / 2.4 MB |

Server side:

| Minute | ALB requests | Task p50 | Task p95 | login-api CPU avg / max |
|---|---|---|---|---|
| 16:20 | 74 | 0.19 s | 0.21 s | 0 / 0% |
| 16:21 | 3,653 | 0.19 s | 1.05 s | 22 / 77% |
| 16:22 | 1,835 | **2.89 s** | **5.43 s** | 49 / **100%** |
| 16:23 | — | — | — | 7 / 39% |

**Auto scaling:** "Setting desired count to 1" at 16:21:13, 23 seconds into the test. This was the scale-in left over from run 5. One task with 3 workers then carried the whole ramp, hit 100% CPU and slowed down.

### Run 8a: VPS, 1,000 users

- **Time:** 29 Oct 11:48:58 – 11:51:35 (2 min 37 s)
- **Result:** ⚠️ Aborted at 790 users: API p95 5,256 ms

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 1,223 | 194 | 3,909 | 4,632 | 7,559 | 8,889 |
| API | 2,354 | 2,132 | 4,642 | 5,256 | 7,761 | 8,889 |
| Page | 148 | 89 | 309 | 410 | 802 | 3,061 |
| TTFB | 1,223 | 194 | 3,909 | 4,632 | 7,559 | 8,889 |
| TCP connect | 4 | 0 | 0 | 0 | 92 | 1,171 |
| TLS handshake | 4 | 0 | 0 | 0 | 104 | 1,689 |
| Blocked | 8 | 0 | 0 | 0 | 201 | 1,986 |

| Totals | |
|---|---|
| Requests | 23,084 (148.0/s) |
| Failed | 0 |
| Iterations | 11,064 (70.9/s) |
| Peak users | 790 |
| Data received / sent | 108.0 MB / 3.0 MB |

### Run 8b: AWS, 1,000 users (latest)

- **Time:** 29 Oct 11:53:35 – 11:56:08 (2 min 33 s)
- **Result:** ⚠️ Aborted at 818 users: API p95 5,051 ms

| Metric | avg | median | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| All requests | 658 | 275 | 1,897 | 4,051 | 5,908 | 7,535 |
| API | 1,197 | 430 | 4,078 | 5,051 | 6,368 | 7,535 |
| Page | 134 | 77 | 303 | 375 | 485 | 3,044 |
| TTFB | 657 | 274 | 1,891 | 4,049 | 5,908 | 7,535 |
| TCP connect | 2 | 0 | 0 | 0 | 53 | 1,112 |
| TLS handshake | 2 | 0 | 0 | 0 | 62 | 753 |
| Blocked | 3 | 0 | 0 | 0 | 117 | 1,354 |

| Totals | |
|---|---|
| Requests | 33,294 (218.3/s) |
| Failed | 1 (one load-balancer 5xx) |
| Iterations | 16,103 (105.6/s) |
| Peak users | 818 |
| Data received / sent | 170.9 MB / 3.6 MB |
| Memory | 49% of 2 GB |

Server side:

| Minute | ALB requests | Task p50 | Task p95 | login-api CPU avg / max |
|---|---|---|---|---|
| 11:53 | 512 | 0.19 s | 0.22 s | 4 / 11% |
| 11:54 | 5,671 | 0.19 s | 0.25 s | 45 / 68% |
| 11:55 | 9,130 | 0.43 s | **4.77 s** | **88 / 100%** |

**Auto scaling:** no activity. The test ended about 1 minute after CPU crossed 60%, and only 1 vCPU was free for one more task anyway.

**Conclusion:** both login-api tasks (2 × 1 vCPU, 3 workers each) saturated near 800 users, about 150 API requests per second.

---

## 6. Analysis

### 6.1 How each change affected AWS

| Step | Change | Effect on login-api | Evidence |
|---|---|---|---|
| Run 1 → 3 | 0.25 → 1 vCPU | Reached 200 users (from 142); p95 5.09 s → 2.17 s | CPU 100% → 46% |
| Run 3 → 5 | Daphne → 3 Uvicorn workers | API median 1.61 s → 0.36 s; requests per second 77 → 129 | CPU 46% → 75%: the vCPU is actually used |
| Run 7b → 8b | 1 → 2 tasks minimum (plus 3 workers on all services) | Peak users 669 → 818; requests per second 139 → 218; API median 1.47 s → 0.43 s | 2 tasks saturated at about 9,100 requests per minute |

### 6.2 Why Daphne capped a task at about half a CPU

Daphne runs synchronous Django views in a single worker thread per process. However many vCPUs a task has, one process serves one view at a time, and extra requests wait. Uvicorn with `--workers 3` runs three independent processes, so three views run in parallel.

### 6.3 Why the 1,000-user tests stop

**AWS:**
- **Capacity:** two 1 vCPU tasks handle about 150 API requests per second for this endpoint before latency rises sharply. At this test's pace that is roughly 800 users.
- **Scaling speed:** auto scaling needs several minutes of sustained high CPU, plus about a minute for a task to start. The test reaches 1,000 users in 3 minutes.
- **Quota:** the account allows 12 vCPU of Fargate and the LMS uses 11. Even a fast scale-out could add only one task.

**VPS:**
- Stopped at 720–790 users, with zero errors.
- Throughput levelled off at about 140–150 requests per second.
- Without server metrics, its bottleneck is unknown: CPU, process count, or database.

### 6.4 Shared production database

Both sites read the same production database on every API call. Some of each site's limit may be database time, especially from AWS (Stockholm), if the database is closer to the VPS. This has not been measured.

---

## 7. Recommendations

1. **Request a Fargate vCPU quota increase** (for example 12 → 40) for the AWS account. This is the main limit on AWS scaling, and it blocks re-enabling chat and audit-api.
2. **Give login-api more starting capacity** before the next 1,000-user test: a 3rd task (fits in the spare vCPU), or larger tasks (2 vCPU with 5–6 workers).
3. **Apply the pending `cpu_target = 50`** and consider a slower ramp, so auto scaling has time to react.
4. **Re-test with a learner account**, so the real learner home calls and database load are covered.
5. **Collect VPS server metrics** (CPU, memory, database time) during the next VPS run.
6. **Enable load-balancer access logs** on AWS, so any 5xx can be traced to its cause.
7. **Run the load generator inside AWS** for tests well above 1,000 users, to rule out the single client connection.
8. **Restart image-uploader** when it's needed again (`terraform apply` in `Image_uploader/infrastructure`). It is currently stopped.

---

## 8. Current AWS configuration (after run 8b)

| Item | Value |
|---|---|
| Services running | 7: login, learner, curriculum, enrolment (2 tasks each); coach, quiz, engagement (1 task each) |
| Removed for now | chat, audit-api (`disabled_services`); their URLs are served by curriculum-api |
| Task size | 1 vCPU / 2 GB |
| App server | Uvicorn 0.34.0, 3 workers per container |
| Auto scaling | 60% average CPU (50% pending), up to 4 tasks per service |
| Updates | 2-task services replace one task at a time; 1-task services start the new task first |
| Fargate vCPU in use | 11 of 12 (image-uploader stopped) |
| Approximate cost | About $14–15/day for 11 tasks at 1 vCPU / 2 GB, plus fixed costs (load balancer, NAT gateway, Valkey) |
| Stop when idle | `terraform apply -var desired_count=0` |

---

## 9. How to repeat

```bash
cd infrastructure/loadtest
# Account in infrastructure/loadtest.env (git-ignored): LOADTEST_EMAIL=..., LOADTEST_PASSWORD=...

# 200 users, 10-minute hold
HOLD=10m BASE_URL=https://lms-aws.kentbusinesscollege.net ./run.sh

# 1,000 users, as in runs 7 and 8 (one site at a time)
PEAK_VUS=1000 HOLD=10m BASE_URL=https://lms.kentbusinesscollege.org ./run.sh
PEAK_VUS=1000 HOLD=10m BASE_URL=https://lms-aws.kentbusinesscollege.net ./run.sh
```

Run one site at a time: both use the same production database.
