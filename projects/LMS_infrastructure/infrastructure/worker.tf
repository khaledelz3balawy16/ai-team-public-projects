# ------------------------------------------------------------
# Session results worker: Teams recordings, attendance and transcripts
# (SharePoint/Graph -> Bunny), run in the background instead of on web
# requests. One task, no load balancer, same backend image and settings as
# the API services.
#
# It runs `manage.py process_session_results --scheduled --limit 10` in a
# loop: one batch, then a pause of session_worker_pause_seconds, forever.
# A failed batch (jobs needing retry) doesn't stop the loop; if the task
# itself stops, ECS starts a new one.
#
# Deploys: the pipeline restarts every service in the cluster, so this worker
# moves to each new backend image together with the APIs.
# Only ONE place may run this: the web services keep SESSION_RESULTS_AUTOMATIC
# off (ecs.tf), and the VPS's own scheduler/timer must be stopped.
# ------------------------------------------------------------

variable "session_worker_enabled" {
  description = "Run the session results worker (Teams recordings to Bunny)"
  type        = bool
  default     = true
}

variable "session_worker_pause_seconds" {
  description = "Pause between the end of one batch and the start of the next"
  type        = number
  default     = 60
}

variable "session_review_seconds" {
  description = "How often the worker runs review_session_recordings (the app reviews in 5-minute slots)"
  type        = number
  default     = 300
}

variable "session_worker_cpu" {
  description = "Recording worker CPU units; 1024 restores the previous allocation"
  type        = number
  default     = 512
  validation {
    condition     = contains([512, 1024], var.session_worker_cpu)
    error_message = "Use 512 or 1024 CPU units for the recording worker."
  }
}

variable "session_worker_memory" {
  description = "Recording worker memory in MiB; 3072 restores the previous allocation"
  type        = number
  default     = 2048
  validation {
    condition     = contains([2048, 3072], var.session_worker_memory)
    error_message = "Use 2048 or 3072 MiB for the recording worker."
  }
}

locals {
  worker_name = "session-worker"

  # sh is PID 1: on stop, ECS sends it SIGTERM; the current batch finishes
  # (up to stopTimeout) and the loop then exits instead of starting another
  #
  # Every session_review_seconds it also runs review_session_recordings (a
  # small slice of saved recordings, HEAD only; confirmed missing files are
  # queued for this same worker). The web services' built-in reviewer thread
  # is off with SESSION_RESULTS_AUTOMATIC, so this loop is its scheduler.
  # Never --full here: that is an operator audit that queues every gap.
  session_worker_command = join(" ", [
    "stop=0; last_review=0; trap 'stop=1' TERM INT;",
    "while [ \"$stop\" = 0 ]; do",
    "python -u manage.py process_session_results --scheduled --limit 10",
    "|| echo \"session worker: batch exited with status $? (jobs needing retry are retried later)\";",
    "[ \"$stop\" = 0 ] || break;",
    "now=$(date +%s);",
    "if [ $((now - last_review)) -ge ${var.session_review_seconds} ]; then",
    "last_review=$now;",
    "python -u manage.py review_session_recordings",
    "|| echo \"session worker: recording review exited with status $? (retried next pass)\";",
    "fi;",
    "[ \"$stop\" = 0 ] || break;",
    "sleep ${var.session_worker_pause_seconds} & wait $!;",
    "done; echo 'session worker: stopped'",
  ])
}

resource "aws_ecs_task_definition" "session_worker" {
  count = var.session_worker_enabled ? 1 : 0

  family                   = "${local.name}-${local.worker_name}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.session_worker_cpu
  memory                   = var.session_worker_memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  # Recordings that go to Azure are streamed through a temporary file
  ephemeral_storage {
    size_in_gib = 50
  }

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name      = "worker"
    image     = local.app_image
    essential = true
    command   = ["sh", "-c", local.session_worker_command]

    # Same settings as the web services (SESSION_RESULTS_AUTOMATIC stays off:
    # this loop is the scheduler)
    environment = [for k, v in merge(local.app_environment, { WEB_CONCURRENCY = "1" }) : { name = k, value = v }]
    secrets = [
      for k in local.app_secret_keys :
      { name = k, valueFrom = "${aws_secretsmanager_secret.app.arn}:${k}::" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = local.worker_name
      }
    }

    # Time for the current batch to finish when ECS stops the task (Fargate maximum)
    stopTimeout = 120
  }])
}

resource "aws_ecs_service" "session_worker" {
  count = var.session_worker_enabled ? 1 : 0

  name            = local.worker_name
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.session_worker[0].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.app[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }

  # Never two workers: stop the old one before starting the new one on a
  # deploy (jobs are leased in the database, so a short gap is harmless)
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  propagate_tags = "SERVICE"

  depends_on = [aws_secretsmanager_secret_version.app, aws_ecs_cluster_capacity_providers.main]
}
