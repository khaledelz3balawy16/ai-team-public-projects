variable "aws_region" {
  description = "AWS region; London, next to the Neon databases (eu-west-2)"
  type        = string
  default     = "eu-west-2"
}

variable "project" {
  description = "Short name used as a prefix in resource names"
  type        = string
  default     = "lms"
}

variable "environment" {
  description = "Environment name; this stack is the AWS staging copy"
  type        = string
  default     = "staging"
}

# ---- Network ----

variable "vpc_cidr" {
  description = "Address range of the LMS VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "nat_per_az" {
  description = "One NAT gateway per zone (no single point of failure for outbound traffic) instead of one in zone A; each costs ~$1.1/day plus data"
  type        = bool
  default     = false
}

variable "availability_zones" {
  description = "Zones to spread subnets and tasks across (London has a, b, c and d)"
  type        = list(string)
  default     = ["eu-west-2a", "eu-west-2b", "eu-west-2c"]
}

# ---- App ----

# One ECS service per API, mirroring the VPS (one process per port behind
# the proxy). Every service runs the same image and the full Django app;
# the load balancer only decides which one handles a path.
variable "api_services" {
  description = "API name => container port and the URL paths routed to it (max 5 paths each)"
  type = map(object({
    port  = number
    paths = list(string)
  }))
  default = {
    curriculum_api = { port = 8001, paths = ["/curriculum_api/*"] }
    coach_api      = { port = 8002, paths = ["/coach_api/*"] }
    quiz_api       = { port = 8003, paths = ["/quiz_api/*"] }
    learner_api    = { port = 8004, paths = ["/learner_api/*"] }
    engagement_api = { port = 8005, paths = ["/engagement_api/*"] }
    audit_api      = { port = 8006, paths = ["/audit_api/*"] }
    chat           = { port = 8007, paths = ["/ws/*", "/api/chat/*"] }
    enrolment_api  = { port = 8008, paths = ["/enrolment_api/*"] }
    login_api      = { port = 8009, paths = ["/login_api/*"] }
  }
}

# URL prefixes CloudFront sends to the load balancer (Django); everything
# else is the React app from S3. Same list as the dev proxy in
# frontend/vite.config.ts, plus the Django admin.
variable "backend_paths" {
  description = "CloudFront path patterns served by the backend"
  type        = list(string)
  default = [
    "/api/*",
    "/ws/*",
    "/curriculum_api/*",
    "/coach_api/*",
    "/quiz_api/*",
    "/learner_api/*",
    "/engagement_api/*",
    "/audit_api/*",
    "/hours_test_api/*",
    "/manual_audit_api/*",
    "/enrolment_api/*",
    "/login_api/*",
    "/progress_reviews_api/*",
    "/django_admin/*",
    # MCP server for AI connectors (ChatGPT/Claude) and its OAuth sign-in
    # (backend mcp_api; answers 404 unless MCP_ENABLED is on)
    "/mcp",
    "/mcp/*",
    "/oauth/*",
    "/.well-known/oauth-*",
  ]
}

variable "disabled_services" {
  description = "APIs from api_services not deployed for now (no ECS service, target group or routing rule); their paths fall through to default_service, which runs the same Django app"
  type        = list(string)
  default     = ["chat", "audit_api"]

  validation {
    condition     = !contains(var.disabled_services, var.default_service)
    error_message = "default_service must stay enabled: it receives the disabled services' paths."
  }
}

variable "default_service" {
  description = "Service that receives every path not listed in api_services"
  type        = string
  default     = "curriculum_api"
}

variable "task_cpu" {
  description = "Fargate CPU units per task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Fargate memory per task in MiB (1 vCPU allows 2048-8192)"
  type        = number
  default     = 2048
}

variable "image_tag" {
  description = "Tag of the backend image in ECR that every service runs"
  type        = string
  default     = "staging"
}

variable "desired_count" {
  description = "Running tasks per API service (0 = stop all services to save cost)"
  type        = number
  default     = 1
}

variable "web_workers" {
  description = "Uvicorn worker processes per container (WEB_CONCURRENCY); each uses ~150-250 MB"
  type        = number
  default     = 3
}

variable "max_count" {
  description = "Most tasks auto scaling may run per API service (unless service_max_counts says otherwise)"
  type        = number
  default     = 2
}

variable "service_max_counts" {
  description = "Services that may scale beyond max_count (api name => most tasks). At these limits the three 2 vCPU services alone could reach 540 vCPU, far above the account's 128 vCPU Fargate On-Demand quota: ECS can't start tasks past the quota until it is raised"
  type        = map(number)
  default = {
    learner_api    = 90
    login_api      = 90
    curriculum_api = 90 # default_service: also gets every unrouted path
    engagement_api = 10
    enrolment_api  = 10
    quiz_api       = 10
    coach_api      = 10
  }
}

variable "fargate_vcpu_quota" {
  description = "Fargate On-Demand vCPU limit to request from AWS (0 = don't request; new accounts start at 12)"
  type        = number
  default     = 0
}

variable "spot_scale_out" {
  description = "Tasks above each service's minimum run on Fargate Spot (separate 12 vCPU limit, ~70% cheaper, may be stopped with 2 minutes' notice and replaced)"
  type        = bool
  default     = false
}

variable "burst_scale_out" {
  description = "Add the burst step-scaling rule (burst_step tasks at once above burst_cpu_threshold) on top of target tracking"
  type        = bool
  default     = true
}

variable "burst_cpu_threshold" {
  description = "Average CPU % at which a service adds burst_step tasks at once (on top of target tracking), so a sudden surge doesn't wait ~3 minutes"
  type        = number
  default     = 59
}

variable "burst_step" {
  description = "Tasks added at once when CPU passes burst_cpu_threshold"
  type        = number
  default     = 6
}

variable "fast_scale_out" {
  description = "Also trigger the burst rule from the app's 10-second load metric (LMS/App ConcurrentRequests), so a surge adds tasks within ~30 s instead of minutes; needs a backend image with config/load_metric.py"
  type        = bool
  default     = true
}

variable "fast_concurrency_threshold" {
  description = "Average requests in progress per worker process that counts as overloaded (a worker serves Django views one at a time, so above ~1 they queue)"
  type        = number
  default     = 2
}

variable "headroom_tasks" {
  description = "Spare tasks kept running ahead of the load: auto scaling aims for (busy tasks + headroom_tasks), e.g. 4 busy -> 6 running, 6 busy -> 8 (0 = off). Uses the app's load metric, like fast_scale_out"
  type        = number
  default     = 2
}

variable "busy_concurrency" {
  description = "Average requests in progress per worker at which a task counts as busy for headroom_tasks (1 = every worker always handling a request)"
  type        = number
  default     = 0.7
}

variable "daytime_min_counts" {
  description = "Higher minimum tasks during class hours (api name => tasks), so capacity is running before learners arrive; empty = no schedule"
  type        = map(number)
  default = {
    # 3 since 10 Nov 2026: the busiest week so far (29 learners in 5 min)
    # peaked at 12% CPU on ~4 tasks; headroom and burst scaling add more
    learner_api    = 3
    login_api      = 3
    curriculum_api = 3
    # Same as their night minimum: listing them gives them the morning/evening
    # schedule, which is what sets min_capacity (Terraform leaves it alone)
    engagement_api = 3
    enrolment_api  = 3
    quiz_api       = 3
    coach_api      = 3
  }
}

variable "daytime_start" {
  description = "When daytime_min_counts starts (App Auto Scaling cron, in daytime_timezone); 15 minutes before the 09:00 start, so the tasks are running when learners arrive"
  type        = string
  default     = "cron(45 8 ? * MON-FRI *)"
}

variable "daytime_end" {
  description = "When the minimum goes back to normal (App Auto Scaling cron, in daytime_timezone); working hours end at 18:00"
  type        = string
  default     = "cron(0 18 ? * MON-FRI *)"
}

variable "daytime_timezone" {
  description = "Time zone of daytime_start/daytime_end"
  type        = string
  default     = "Europe/London"
}

variable "service_sizes" {
  description = "Services sized differently from task_cpu/task_memory/web_workers (api name => size). The two busy APIs get 2 vCPU / 4 GB (learner-api ran out of memory headroom at 2 GB); quiet ones shrink so normal running fits the 12 vCPU quota (11.5 vCPU)"
  type = map(object({
    cpu     = number
    memory  = number
    workers = number
  }))
  default = {
    # 8 workers x ~600 MB under load needs more than 4 GB (learner-api reached 98% of 4 GB at 5 workers)
    learner_api    = { cpu = 2048, memory = 8192, workers = 8 }
    login_api      = { cpu = 2048, memory = 8192, workers = 8 } # sign-in (password hashing) is CPU bound
    curriculum_api = { cpu = 2048, memory = 8192, workers = 8 }
    coach_api      = { cpu = 1024, memory = 3072, workers = 3 }
    # 2 workers in 1 GB ran out of memory and workers died (502s) on 2026-11-05
    engagement_api = { cpu = 1024, memory = 3072, workers = 3 }
    enrolment_api  = { cpu = 1024, memory = 3072, workers = 3 }
    quiz_api       = { cpu = 1024, memory = 3072, workers = 3 }
    chat           = { cpu = 256, memory = 1024, workers = 1 }
    audit_api      = { cpu = 512, memory = 1024, workers = 2 }
  }
}

variable "service_min_counts" {
  description = "Services that always run more than desired_count tasks (api name => minimum); the busiest APIs, so a spike doesn't wait for auto scaling"
  type        = map(number)
  default = {
    login_api      = 2
    learner_api    = 2
    curriculum_api = 2
    enrolment_api  = 3
    engagement_api = 3
    quiz_api       = 3
    coach_api      = 3
  }
}

variable "cpu_target" {
  description = "Average CPU % per service that auto scaling keeps tasks at"
  type        = number
  default     = 60 # headroom: at 100% CPU requests queue and the Neon pool times out
}

variable "domain_name" {
  description = "The live domain (CNAME at Hostinger -> CloudFront); switched from lms-aws.kentbusinesscollege.net on 2026-11-04"
  type        = string
  default     = "lms.kentbusinesscollege.org"
}

variable "certificate_extra_names" {
  description = "Extra names on the CloudFront certificate (the issued certificate also covers the retired lms-aws name; changing this replaces the certificate)"
  type        = list(string)
  default     = ["lms-aws.kentbusinesscollege.net"]
}

variable "attach_domain" {
  description = "Serve domain_name on CloudFront. Turn on only after its certificate is ISSUED (validation record added in Hostinger) and no other CloudFront distribution, e.g. the old Stockholm stack, still uses the name"
  type        = bool
  default     = true
}

variable "public_domain" {
  description = "Override for the address used in links, emails and Microsoft/Google sign-in callbacks; empty = domain_name"
  type        = string
  default     = ""
}

variable "app_hosts" {
  description = "Extra public host names the site is served on, besides CloudFront's and domain_name"
  type        = list(string)
  default     = []
}

# Values live only in secrets.auto.tfvars (git-ignored), generated from backend/.env
variable "app_secrets" {
  description = "App settings from backend/.env (name => value), stored in Secrets Manager"
  type        = map(string)
  sensitive   = true
  default     = {}
}

variable "app_secrets_version" {
  description = "Changes when app_secrets change (set by scripts/env_to_tfvars.py), to send the new values to AWS"
  type        = number
  default     = 1
}

variable "lb_algorithm" {
  description = "How the load balancer picks a task: round_robin, or least_outstanding_requests (sends each request to the task with the fewest in progress; much better at 2000+ users)"
  type        = string
  default     = "round_robin"
}

variable "health_check_path" {
  description = "Path the load balancer polls on each task; must return 200 without host validation"
  type        = string
  default     = "/health/"
}

# ---- Valkey (ElastiCache) ----

variable "valkey_engine_version" {
  description = "Valkey major.minor version"
  type        = string
  default     = "8.1"
}

variable "valkey_node_type" {
  description = "Size of each Valkey node"
  type        = string
  default     = "cache.t4g.medium"
}
