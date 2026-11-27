# LMS AWS load test — 2,000 and 5,000 users (29 Oct 2026)

AWS staging copy only (`https://lms-aws.kentbusinesscollege.net`), eu-north-1.
The site still uses the **production databases**, so every test kept the automatic stop
(abort when 5% of requests fail or API p95 passes 5 s).

## Summary

| Run | Users | Setup | Result | Errors | API median | API p95 | Peak API req/s |
|---|---|---|---|---|---|---|---|
| 9 | 2,000 | auto scaling from 2 login tasks | **Aborted at ~877 users** (2 min 20 s) | 0.01% | 0.23 s | 5.1 s | ~140 (average) |
| 10 | 2,000 | login-api pre-scaled to 14 tasks | **Passed** | 0.00% | 0.19 s | 0.26 s | 901 |
| 11 | 5,000 | 14 tasks, round-robin routing | **Aborted at the end of the hold** | 0.35% | 0.19 s | 5.1 s (p99 46 s) | 989 |
| 12 | 5,000 | 14 tasks, least-outstanding-requests routing | **Completed; no abort** | 0.00% (74 of 1.44 M) | 0.83 s | 2.31 s | **1,385** |

**Bottom line**
- **Up to ~2,500 users:** fast. API p95 stays under 1 s.
- **~3,000 users:** login-api CPU reaches 100%. This is the ceiling of 24 vCPU, about 1,380 API requests per second.
- **5,000 users:** still served with no errors, but slowly: median ~1.5 s, p95 ~2.6 s at peak.
- **These results need pre-warming.** From a cold start (2 tasks), auto scaling is too slow for a fast surge; that test stopped at ~880 users.

## What was changed

### Infrastructure (Terraform, `infrastructure/`)

| Area | Before | After | File |
|---|---|---|---|
| Fargate capacity | 12 vCPU On-Demand only | **12 On-Demand + 12 Spot = 24 vCPU.** Each service's minimum tasks run On-Demand; tasks added by auto scaling run on Fargate Spot. | `ecs.tf` (`aws_ecs_cluster_capacity_providers`, `capacity_provider_strategy`), `variables.tf` (`spot_scale_out`) |
| Maximum tasks per service | 4 for every service | login-api **14**, learner-api **8**, curriculum-api **8**, others 4 | `autoscaling.tf`, `variables.tf` (`service_max_counts`) |
| Scaling speed | target tracking only (needs ~3 min of high CPU) | Added a **burst rule:** CPU > 75% for 1 minute adds 3 tasks at once. Target tracking (55%) still handles the rest and scale-in. | `autoscaling.tf` (`api_burst` policy + CloudWatch alarm), `variables.tf` |
| Load balancer routing | round robin | **least outstanding requests.** Each request goes to the task with the fewest requests in progress. | `alb.tf` |
| NAT gateways | 1 (zone A) | **3, one per zone.** Zone A keeps its existing IP. Neon has no IP allow-list, so the new IPs need no change. | `network.tf`, output `nat_public_ips` |
| Valkey (cache) | 2 × cache.t4g.micro | **2 × cache.t4g.medium** | `variables.tf`, `valkey.tf` (`apply_immediately = true`) |
| Load generator | this laptop | **2 × EC2 m7i-flex.large** (the Free plan allows only free-tier types), created only when `loadgen_enabled = true`. Reached through SSM; no inbound ports. **Now removed.** | `loadgen.tf` (new) |

Not changed:
- **Task size:** 1 vCPU / 2 GB, 3 workers. Memory stayed ≤ 56%.
- **Database pooling:** it was already on (Neon pooler + app pool).
- **Neon compute size:** production; not touched.

### Load-test tooling (`infrastructure/loadtest/`)
- `lms.js`: the ramp length is now adjustable (`RAMP`, default `2m` as before).
- `run-aws.sh` (new):
  - runs `lms.js` on the EC2 load generators through SSM;
  - splits the users between instances;
  - fetches each instance's results into `results/`;
  - reads the account on the instance from SSM `/lms-staging/loadtest/env`, so it never passes through the script.

### Temporary changes (already reverted)
- **Pre-scaling:** login-api auto scaling was set to min = max = 14 for runs 10–12 using the AWS CLI. It's back to the Terraform range of 2–14 and scales in on its own.
- **Load generators:** removed after the tests.

## Run details

All runs used:
- **Account:** one staff account (`role=admin`) signed in once and shared by every virtual user.
- **Each iteration:** the page `/learner/home` (CloudFront/S3), then API `/login_api/me/`, then a 1–3 s think time.
- **Load source:** 2 load generators inside AWS, each running half of the users.

### Run 9: 2,000 users, cold start (auto scaling only)

| Setting | Value |
|---|---|
| Ramp | 1 min to 500 users, then 5 min to 2,000 |
| Stopped | at 2 min 20 s, with **877 users** |
| Reason | API p95 reached 5.1 s |
| Errors | 0.01% |
| login-api CPU in the last minute | average 58%, max 87% |

- **No scaling happened:** login-api stayed at 2 tasks.
  - Target tracking needs about 3 minutes of high CPU.
  - The burst rule needs one full minute above 75%.
  - New tasks then take another ~2 minutes to start.
- **The surge outran all of it.** The same 2-task limit as run 8b (818 users).

### Run 10: 2,000 users, login-api pre-scaled to 14 tasks

| Metric | Value |
|---|---|
| Requests | 702,138, of which 5 failed (0.00%) |
| API (k6) | median 0.19 s, p95 0.26 s, p99 6.2 s |
| Page (CloudFront) | p95 0.07 s |
| Peak API rate (ALB) | 901 req/s (≈ 0.45 API req/s per user) |
| login-api CPU | average 43–57% |
| Memory | ≤ 52% |

- The run passed, but in the last 3 minutes ALB p95 rose to 2.4–6.4 s while average CPU was only ~50%. See run 11 for the cause.

### Run 11: 5,000 users, round-robin routing

| Setting | Value |
|---|---|
| Ramp | 1 min to 1,250, then 6 min to 5,000, then hold 3 min |
| Stopped | at 10 min 14 s, near the end of the hold |
| Requests | 1,055,092, of which 3,713 failed (0.35%) |
| API | median 0.19 s, p95 5.1 s, **p99 46 s** |
| Throughput | flat at **~970–990 API req/s** from about 2,000 users onward |
| login-api CPU | average ~60%, max 100% |

- **Cause:** a single Spot task (zone C) out of 14 fell behind.
- **Then:** its database connection pool ran dry, and from 17:17 it failed requests with `PoolTimeout`. All 3,700 server errors came from that one task.
- **Why it hurt so much:** round robin kept sending it an equal 1/14 share of requests. Those requests queued for 45 s or failed, while the other 13 tasks had spare CPU.
- **It wasn't the new NAT gateways:** other tasks in zone C were fine.

### Run 12: 5,000 users, least-outstanding-requests routing (after the fix)

| Metric | Value |
|---|---|
| Duration | full 10.5 min, **no abort** |
| Requests | 1,439,704, of which 74 failed (**0.00%**) |
| Failures | the 74 are ALB 502s during a task replacement; no app errors |
| API (k6, whole run) | median 0.83 s, p95 2.31 s, p99 2.89 s, max 4.7 s |
| Page | p95 0.07 s |

Minute by minute (load balancer and login-api):

| Time | Approx. users | API req/s | p50 | p95 | CPU avg / max |
|---|---|---|---|---|---|
| 17:28 | 1,250 | 700 | 0.19 s | 0.27 s | 42 / 75% |
| 17:29 | 1,900 | 979 | 0.19 s | 0.35 s | 59 / 84% |
| 17:30 | 2,500 | 1,251 | 0.36 s | 0.94 s | 78 / 97% |
| 17:31 | 3,100 | 1,382 | 0.83 s | 1.67 s | 94 / 100% |
| 17:32–17:36 | 3,700–5,000 | ~1,375 | 1.3–1.6 s | 2.1–2.7 s | **98 / 100%** |

- **Throughput stopped at ~1,380 API req/s** because all 14 login-api tasks were at full CPU. That's ~98 req/s per vCPU.
- **Above ~3,000 users, extra users wait** rather than fail.
- **Valkey:** t4g.medium, healthy. **Memory:** ≤ 56%.

## Analysis

1. **The new limit is login-api CPU: 14 vCPU ≈ 1,380 req/s.**
   - That's about 2,500 users with fast responses, or 5,000 users with 1.5–2.6 s responses.
   - More users at the same speed need more vCPU, which means a quota increase.
   - At ~98 req/s per vCPU and a 0.45 req/s-per-user rate, comfortable 5,000-user service needs roughly **25–30 vCPU for login-api alone**.
2. **Least-outstanding-requests routing was the biggest single improvement.**
   - The same 14 tasks went from ~990 to ~1,380 req/s.
   - p99 dropped from 46 s to 2.9 s.
3. **Cold-start scaling can't follow a fast surge.** Real peaks (term start, live-session times) need:
   - **scheduled pre-scaling** (raise the minimum before the peak), or
   - a permanently higher minimum.
4. **The database held up in this test.**
   - Tens of millions of DB-backed `/me` calls over the day went through without database errors, except on the one stuck task in run 11.
   - However, `/login_api/me/` is a light query. Real learner pages do much more database work.

## Limits of these results

- **Only one API was exercised.** The test account is staff, so each iteration called only `/login_api/me/`. Learner pages (dashboard, training plan, attendance) are heavier and were not tested. A learner account is needed for that.
- **One shared session.** Real users each have their own session and cache entries.
- **Production database.** Every request hit the production database while live learners were using the VPS (about 14:50–15:40 UK time). No database errors were seen, but database load wasn't measured on the Neon side.
- **Spot tasks can be interrupted.** A replacement takes ~2 minutes and caused the 74 502s in run 12.
- **Unexplained task stall.** Why the one task stalled in run 11 is not fully explained: probably CPU saturation followed by a pool deadline. Least-outstanding routing avoids the impact, not the root cause.

## Ongoing cost of the upgrade (approx.)

| Item | Extra cost |
|---|---|
| 2 extra NAT gateways | ~$2.2/day plus data |
| Valkey t4g.micro → t4g.medium (2 nodes) | ~+$2.5/day |
| Spot tasks | only while scaled out, ~$0.012/hour per 1 vCPU / 2 GB task |
| Load generators | removed; ~$0.20/hour when enabled |

## Follow-ups

1. **Pre-scale before known peaks.** Add a scheduled action that raises login-api, learner-api and curriculum-api minimums before peak times.
2. **Request a Fargate quota increase** (On-Demand and/or Spot) if 5,000 users must get sub-second responses.
3. **Re-test with a learner account** to load learner-api and the heavier database queries, ideally against a Neon branch instead of production.
4. **Delete the test credentials when no longer needed:**
   `aws ssm delete-parameter --region eu-north-1 --name /lms-staging/loadtest/env`
5. **Running the load generators again:**
   - `terraform apply -var loadgen_enabled=true`
   - then `PEAK_VUS=… RAMP=… HOLD=… BASE_URL=… loadtest/run-aws.sh`
   - then `terraform apply` to remove them.

Raw results: `results/lms-aws_kentbusinesscollege_net-20261029-{165339,165839,171041,172659}-<instance>.{txt,json}`, scaling log `results/scaling-watch-run9.log`.
