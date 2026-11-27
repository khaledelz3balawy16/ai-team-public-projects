# ------------------------------------------------------------
# Night mode: outside class hours one small service ("night-api") serves the
# paths of the big APIs (var.night_mode_services) and those services stop.
#
# Every service runs the same full Django app, so night-api is simply
# registered in the big services' target groups at the same time (an ECS
# service can sit in up to 5). The load balancer rules never change: at
# night the target groups just contain night-api's tasks instead.
#
# Schedule (var.daytime_timezone, Monday-Friday; weekends stay in night mode):
#   19:45  night-api starts (var.night_min_tasks)       - both serve for 15 min
#   20:00  big services -> 0 (open requests drain first, deregistration_delay)
#   07:30  big services start at their daytime minimum  - both serve for 30 min
#   08:00  night-api -> 0
# Auto scaling adds night-api tasks under load (CPU target + burst rule).
# Empty var.night_mode_services turns all of this off.
# ------------------------------------------------------------

locals {
  night_services = [for k in var.night_mode_services : k if contains(keys(local.api_services), k)]
  night_enabled  = length(local.night_services) > 0 && var.desired_count > 0
  # Any port inside the existing ALB -> app security group range; each task
  # has its own IP, so sharing a number with a day service doesn't clash
  night_port = local.api_port_min
}

resource "aws_ecs_task_definition" "night" {
  count = local.night_enabled ? 1 : 0

  family                   = "${local.name}-night-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.night_size.cpu
  memory                   = var.night_size.memory
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([{
    name      = "app"
    image     = local.app_image
    essential = true

    portMappings = [{ containerPort = local.night_port, protocol = "tcp" }]

    environment = [
      for k, v in merge(local.app_environment, {
        PORT                = tostring(local.night_port)
        WEB_CONCURRENCY     = tostring(var.night_size.workers)
        LOAD_METRIC_SERVICE = "night-api"
      }) :
      { name = k, value = v }
    ]

    secrets = [
      for k in local.app_secret_keys :
      { name = k, valueFrom = "${aws_secretsmanager_secret.app.arn}:${k}::" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "night-api"
      }
    }

    stopTimeout = 60
  }])
}

resource "aws_ecs_service" "night" {
  count = local.night_enabled ? 1 : 0

  name            = "night-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.night[0].arn
  desired_count   = 0 # the schedule below starts it in the evening

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }

  network_configuration {
    subnets          = aws_subnet.app[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }

  # One registration per big service's target group
  dynamic "load_balancer" {
    for_each = toset(local.night_services)
    content {
      target_group_arn = aws_lb_target_group.api[load_balancer.value].arn
      container_name   = "app"
      container_port   = local.night_port
    }
  }

  health_check_grace_period_seconds  = 60
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  availability_zone_rebalancing      = "ENABLED"
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  propagate_tags = "SERVICE"

  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_lb_listener.http, aws_lb_listener_rule.api, aws_secretsmanager_secret_version.app, aws_ecs_cluster_capacity_providers.main]
}

# Range 0..night_max_tasks. Only the schedule moves the minimum; an apply at
# night therefore never stops the tasks that are serving.
resource "aws_appautoscaling_target" "night" {
  count = local.night_enabled ? 1 : 0

  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.night[0].name}"
  min_capacity       = 0
  max_capacity       = var.night_max_tasks

  lifecycle {
    ignore_changes = [min_capacity]
  }
}

resource "aws_appautoscaling_policy" "night_cpu" {
  count = local.night_enabled ? 1 : 0

  name               = "${local.name}-night-api-cpu"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.night[0].service_namespace
  scalable_dimension = aws_appautoscaling_target.night[0].scalable_dimension
  resource_id        = aws_appautoscaling_target.night[0].resource_id

  target_tracking_scaling_policy_configuration {
    target_value = var.cpu_target
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    scale_out_cooldown = 60
    scale_in_cooldown  = 300
  }
}

# Same burst rule as the day services: CPU over burst_cpu_threshold for a
# minute adds burst_step tasks at once
resource "aws_appautoscaling_policy" "night_burst" {
  count = local.night_enabled && var.burst_scale_out ? 1 : 0

  name               = "${local.name}-night-api-burst"
  policy_type        = "StepScaling"
  service_namespace  = aws_appautoscaling_target.night[0].service_namespace
  scalable_dimension = aws_appautoscaling_target.night[0].scalable_dimension
  resource_id        = aws_appautoscaling_target.night[0].resource_id

  step_scaling_policy_configuration {
    adjustment_type         = "ChangeInCapacity"
    cooldown                = 60
    metric_aggregation_type = "Average"
    step_adjustment {
      metric_interval_lower_bound = 0
      scaling_adjustment          = var.burst_step
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "night_burst" {
  count = local.night_enabled && var.burst_scale_out ? 1 : 0

  alarm_name          = "${local.name}-night-api-cpu-burst"
  alarm_description   = "CPU above ${var.burst_cpu_threshold}% for a minute: add ${var.burst_step} tasks"
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 60
  evaluation_periods  = 1
  threshold           = var.burst_cpu_threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.night[0].name
  }
  alarm_actions = [aws_appautoscaling_policy.night_burst[0].arn]
}

# ---- the schedule ----

resource "aws_appautoscaling_scheduled_action" "night_api_start" {
  count = local.night_enabled ? 1 : 0

  name               = "${local.name}-night-api-start"
  service_namespace  = aws_appautoscaling_target.night[0].service_namespace
  scalable_dimension = aws_appautoscaling_target.night[0].scalable_dimension
  resource_id        = aws_appautoscaling_target.night[0].resource_id
  schedule           = var.night_api_start
  timezone           = var.daytime_timezone

  scalable_target_action {
    min_capacity = var.night_min_tasks
    max_capacity = var.night_max_tasks
  }
}

resource "aws_appautoscaling_scheduled_action" "night_api_stop" {
  count = local.night_enabled ? 1 : 0

  name               = "${local.name}-night-api-stop"
  service_namespace  = aws_appautoscaling_target.night[0].service_namespace
  scalable_dimension = aws_appautoscaling_target.night[0].scalable_dimension
  resource_id        = aws_appautoscaling_target.night[0].resource_id
  schedule           = var.night_api_stop
  timezone           = var.daytime_timezone

  scalable_target_action {
    min_capacity = 0
    max_capacity = 0
  }
}

# Big services: off in the evening (min = max = 0) ...
resource "aws_appautoscaling_scheduled_action" "big_stop" {
  for_each = local.night_enabled ? toset(local.night_services) : toset([])

  name               = "${local.name}-${replace(each.key, "_", "-")}-night-stop"
  service_namespace  = aws_appautoscaling_target.api[each.key].service_namespace
  scalable_dimension = aws_appautoscaling_target.api[each.key].scalable_dimension
  resource_id        = aws_appautoscaling_target.api[each.key].resource_id
  schedule           = var.night_big_stop
  timezone           = var.daytime_timezone

  scalable_target_action {
    min_capacity = 0
    max_capacity = 0
  }

  # Never before night-api has its start action
  depends_on = [aws_appautoscaling_scheduled_action.night_api_start]
}

# ... and back in the morning at the daytime minimum (daytime_min_counts,
# else their normal minimum) with their normal maximum
resource "aws_appautoscaling_scheduled_action" "big_start" {
  for_each = local.night_enabled ? toset(local.night_services) : toset([])

  name               = "${local.name}-${replace(each.key, "_", "-")}-day-start"
  service_namespace  = aws_appautoscaling_target.api[each.key].service_namespace
  scalable_dimension = aws_appautoscaling_target.api[each.key].scalable_dimension
  resource_id        = aws_appautoscaling_target.api[each.key].resource_id
  schedule           = var.night_big_start
  timezone           = var.daytime_timezone

  scalable_target_action {
    min_capacity = min(lookup(var.daytime_min_counts, each.key, local.min_tasks[each.key]), aws_appautoscaling_target.api[each.key].max_capacity)
    max_capacity = aws_appautoscaling_target.api[each.key].max_capacity
  }
}

# ---- settings ----

variable "night_mode_services" {
  description = "APIs served by night-api outside class hours and stopped meanwhile (max 5: one target group each). Empty = night mode off"
  type        = list(string)
  default     = ["learner_api", "login_api", "curriculum_api"]
  validation {
    condition     = length(var.night_mode_services) <= 5
    error_message = "An ECS service can be registered in at most 5 target groups."
  }
}

variable "night_size" {
  description = "night-api task size: same as the big APIs, since it runs their full load"
  type = object({
    cpu     = number
    memory  = number
    workers = number
  })
  default = { cpu = 2048, memory = 8192, workers = 8 }
}

variable "night_min_tasks" {
  description = "night-api tasks at night (2 = one can fail or be replaced without an outage)"
  type        = number
  default     = 2
}

variable "night_max_tasks" {
  description = "Most night-api tasks auto scaling may add"
  type        = number
  default     = 12
}

variable "night_api_start" {
  description = "When night-api starts (in daytime_timezone); 15 min before the big services stop"
  type        = string
  default     = "cron(45 19 ? * MON-FRI *)"
}

variable "night_big_stop" {
  description = "When the big services stop for the night"
  type        = string
  default     = "cron(0 20 ? * MON-FRI *)"
}

variable "night_big_start" {
  description = "When the big services start again; 30 min before night-api stops so they are healthy first"
  type        = string
  default     = "cron(30 7 ? * MON-FRI *)"
}

variable "night_api_stop" {
  description = "When night-api stops for the day"
  type        = string
  default     = "cron(0 8 ? * MON-FRI *)"
}
