# ------------------------------------------------------------
# Application Load Balancer (diagram: "Application Load Balancer - /api, /ws")
# Lives in the public subnets of all zones; reachable only from CloudFront
# (see security_groups.tf). Like the VPS proxy, it routes each URL prefix to
# its own API service and port (var.api_services).
# ------------------------------------------------------------

resource "aws_lb" "main" {
  name               = "${local.name}-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  # Idle WebSocket (chat) and large evidence uploads need more than the 60s default
  idle_timeout = 300

  tags = { Name = "${local.name}-alb" }
}

# One target group per API service; ECS registers that service's tasks here
resource "aws_lb_target_group" "api" {
  for_each = local.api_services

  name        = "${local.name}-${replace(each.key, "_", "-")}" # e.g. lms-staging-coach-api
  port        = each.value.port
  protocol    = "HTTP"
  target_type = "ip" # required for Fargate
  vpc_id      = aws_vpc.main.id

  # Let in-flight requests finish when a task is replaced or scaled in
  # (CloudFront gives up on a request after 60 s anyway)
  deregistration_delay = 60

  # least_outstanding_requests sends each request to the task with the fewest
  # in progress, so one slow task doesn't keep receiving an equal share and
  # queue them up (seen at 2000+ users with round robin)
  load_balancing_algorithm_type = var.lb_algorithm

  health_check {
    path    = var.health_check_path # answered by config/health.py
    matcher = "200"
    # New tasks count as healthy after 2 checks 10 s apart (20 s instead of
    # 60 s), which shortens every deploy. Removing a task still takes 6
    # failed checks (60 s), so a task that is only busy under load isn't
    # pulled out of service.
    healthy_threshold   = 2
    unhealthy_threshold = 6
    interval            = 10
    timeout             = 5
  }

  tags = { Name = "${local.name}-${replace(each.key, "_", "-")}", Service = each.key }
}

# Port 80 from CloudFront. Paths not matched by a rule below go to the
# default service.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[var.default_service].arn
  }
}

locals {
  # Stable, unique rule priorities (10, 20, 30...) in alphabetical order of ALL
  # services, so turning one off or on does not renumber the others
  api_service_names = sort(keys(var.api_services))
}

# The proxy table: URL prefix -> service
resource "aws_lb_listener_rule" "api" {
  for_each = local.api_services

  listener_arn = aws_lb_listener.http.arn
  priority     = (index(local.api_service_names, each.key) + 1) * 10

  condition {
    path_pattern {
      values = each.value.paths
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[each.key].arn
  }
}
