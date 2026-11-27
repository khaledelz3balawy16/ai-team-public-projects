# ------------------------------------------------------------
# Auto scaling: each API service adds tasks when its average CPU stays
# above var.cpu_target and removes them when it falls again.
# Range: var.desired_count (or its service_min_counts entry) .. var.max_count
# (or its service_max_counts entry) tasks. desired_count = 0 still
# stops everything (min and max both become 0).
# ------------------------------------------------------------

resource "aws_appautoscaling_target" "api" {
  for_each = local.api_services

  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api[each.key].name}"
  min_capacity       = local.min_tasks[each.key]
  max_capacity       = var.desired_count == 0 ? 0 : max(lookup(var.service_max_counts, each.key, var.max_count), local.min_tasks[each.key])

  # The daytime/evening scheduled actions move min_capacity during the day;
  # without this an apply in working hours would drop the daytime minimum
  # back to the night one. Night minimums still come from the evening action.
  # (A changed service_min_counts for a service without a schedule needs
  # terraform apply -replace on its target.)
  lifecycle {
    ignore_changes = [min_capacity]
  }
}

locals {
  # desired_count, raised for the services in service_min_counts; 0 stops all
  min_tasks = {
    for k, v in local.api_services :
    k => var.desired_count == 0 ? 0 : max(var.desired_count, lookup(var.service_min_counts, k, 0))
  }
}

resource "aws_appautoscaling_policy" "api_cpu" {
  for_each = local.api_services

  name               = "${local.name}-${replace(each.key, "_", "-")}-cpu"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.api[each.key].service_namespace
  scalable_dimension = aws_appautoscaling_target.api[each.key].scalable_dimension
  resource_id        = aws_appautoscaling_target.api[each.key].resource_id

  target_tracking_scaling_policy_configuration {
    target_value = var.cpu_target

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_out_cooldown = 60  # add tasks quickly under load
    scale_in_cooldown  = 300 # remove them slowly, so short dips don't cause flapping
  }
}

# Burst (var.burst_scale_out): target tracking needs ~3 minutes of high CPU before it adds tasks.
# When a service's CPU passes burst_cpu_threshold for one minute, add
# burst_step tasks at once; App Auto Scaling uses whichever policy asks for
# more. Scale-in is left to target tracking.
resource "aws_appautoscaling_policy" "api_burst" {
  for_each = var.burst_scale_out ? local.api_services : {}

  name               = "${local.name}-${replace(each.key, "_", "-")}-burst"
  policy_type        = "StepScaling"
  service_namespace  = aws_appautoscaling_target.api[each.key].service_namespace
  scalable_dimension = aws_appautoscaling_target.api[each.key].scalable_dimension
  resource_id        = aws_appautoscaling_target.api[each.key].resource_id

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

resource "aws_cloudwatch_metric_alarm" "api_burst" {
  for_each = var.burst_scale_out ? local.api_services : {}

  alarm_name          = "${local.name}-${replace(each.key, "_", "-")}-cpu-burst"
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
    ServiceName = aws_ecs_service.api[each.key].name
  }

  alarm_actions = [aws_appautoscaling_policy.api_burst[each.key].arn]
}

# Fast burst (var.fast_scale_out): the app reports its average requests in
# progress per worker every 10 seconds (backend config/load_metric.py).
# Two of three 10-second readings above fast_concurrency_threshold trigger
# the same burst rule, ~30 s after a surge starts instead of the minutes the
# once-a-minute ECS CPU metric needs.
resource "aws_cloudwatch_metric_alarm" "api_fast" {
  for_each = var.burst_scale_out && var.fast_scale_out ? local.api_services : {}

  alarm_name          = "${local.name}-${replace(each.key, "_", "-")}-load-fast"
  alarm_description   = "Over ${var.fast_concurrency_threshold} requests in progress per worker for 20 s: add ${var.burst_step} tasks"
  namespace           = "LMS/App"
  metric_name         = "ConcurrentRequests"
  statistic           = "Average"
  period              = 10
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  threshold           = var.fast_concurrency_threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    Service = aws_ecs_service.api[each.key].name
  }

  alarm_actions = [aws_appautoscaling_policy.api_burst[each.key].arn]
}

# Class hours (var.daytime_min_counts): raise the minimum before learners
# arrive and put it back afterwards; auto scaling still adds tasks above it.
resource "aws_appautoscaling_scheduled_action" "daytime_start" {
  for_each = { for k, v in var.daytime_min_counts : k => v if contains(keys(local.api_services), k) }

  name               = "${local.name}-${replace(each.key, "_", "-")}-daytime-start"
  service_namespace  = aws_appautoscaling_target.api[each.key].service_namespace
  scalable_dimension = aws_appautoscaling_target.api[each.key].scalable_dimension
  resource_id        = aws_appautoscaling_target.api[each.key].resource_id
  schedule           = var.daytime_start
  timezone           = var.daytime_timezone

  scalable_target_action {
    min_capacity = min(each.value, aws_appautoscaling_target.api[each.key].max_capacity)
    max_capacity = aws_appautoscaling_target.api[each.key].max_capacity
  }
}

resource "aws_appautoscaling_scheduled_action" "daytime_end" {
  for_each = aws_appautoscaling_scheduled_action.daytime_start

  name               = "${local.name}-${replace(each.key, "_", "-")}-daytime-end"
  service_namespace  = each.value.service_namespace
  scalable_dimension = each.value.scalable_dimension
  resource_id        = each.value.resource_id
  schedule           = var.daytime_end
  timezone           = var.daytime_timezone

  scalable_target_action {
    min_capacity = local.min_tasks[each.key]
    max_capacity = aws_appautoscaling_target.api[each.key].max_capacity
  }
}

# Headroom (var.headroom_tasks): keep that many spare tasks running ahead of
# the load. From the app's load metric, per minute:
#   running tasks = reports / (workers x 6 reports per worker)
#   busy tasks    = running x average requests in progress per worker / busy_concurrency
# The metric below is 100 x (busy + headroom) / running; target tracking
# keeps it at 100, i.e. running = busy + headroom. The load per worker is
# capped at 1.5 so one queueing spike can at most about double the tasks in
# a step (the burst rule adds more on top). Scale-in, as for CPU, only when
# every policy agrees.
resource "aws_appautoscaling_policy" "api_headroom" {
  for_each = var.fast_scale_out && var.headroom_tasks > 0 ? local.api_services : {}

  name               = "${local.name}-${replace(each.key, "_", "-")}-headroom"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.api[each.key].service_namespace
  scalable_dimension = aws_appautoscaling_target.api[each.key].scalable_dimension
  resource_id        = aws_appautoscaling_target.api[each.key].resource_id

  target_tracking_scaling_policy_configuration {
    target_value       = 100
    scale_out_cooldown = 60
    scale_in_cooldown  = 300

    customized_metric_specification {
      metrics {
        id          = "load"
        label       = "Requests in progress per worker"
        return_data = false
        metric_stat {
          stat = "Average"
          metric {
            namespace   = "LMS/App"
            metric_name = "ConcurrentRequests"
            dimensions {
              name  = "Service"
              value = aws_ecs_service.api[each.key].name
            }
          }
        }
      }

      metrics {
        id          = "reports"
        label       = "Load reports per minute"
        return_data = false
        metric_stat {
          stat = "SampleCount"
          metric {
            namespace   = "LMS/App"
            metric_name = "ConcurrentRequests"
            dimensions {
              name  = "Service"
              value = aws_ecs_service.api[each.key].name
            }
          }
        }
      }

      metrics {
        id          = "headroom"
        label       = "Busy plus ${var.headroom_tasks} spare tasks, % of running"
        return_data = true
        expression = format(
          "100 * (MIN([load, load * 0 + 1.5]) / %s + %d / reports)",
          var.busy_concurrency,
          var.headroom_tasks * try(var.service_sizes[each.key].workers, var.web_workers) * 6,
        )
      }
    }
  }
}
