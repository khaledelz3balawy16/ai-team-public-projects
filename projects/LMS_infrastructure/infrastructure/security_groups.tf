# ------------------------------------------------------------
# Security groups: each layer only accepts traffic from the one in front of it
#   CloudFront --80--> ALB --API ports--> ECS tasks --6379--> Valkey
# Note: Terraform removes AWS's default "allow all outbound" rule from groups
# it creates, so every outbound rule here is explicit.
# ------------------------------------------------------------

locals {
  # The API services use one contiguous port range (8001-8009, as on the VPS)
  api_port_min = min([for s in var.api_services : s.port]...)
  api_port_max = max([for s in var.api_services : s.port]...)
}

# AWS-maintained list of CloudFront's addresses that connect to origins
data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

# ---- Load balancer: only CloudFront may connect ----

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "LMS load balancer - HTTP from CloudFront only"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-alb" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_from_cloudfront" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTP from CloudFront edge locations"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront.id
}

resource "aws_vpc_security_group_egress_rule" "alb_to_app" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Forward requests and health checks to the app tasks"
  ip_protocol                  = "tcp"
  from_port                    = local.api_port_min
  to_port                      = local.api_port_max
  referenced_security_group_id = aws_security_group.app.id
}

# ---- App tasks (ECS Fargate): only the load balancer may connect ----

resource "aws_security_group" "app" {
  name        = "${local.name}-app"
  description = "LMS app tasks - app port from the load balancer only" # changing this text forces AWS to replace the group
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-app" }
}

resource "aws_vpc_security_group_ingress_rule" "app_from_alb" {
  security_group_id            = aws_security_group.app.id
  description                  = "HTTP and WebSocket from the load balancer"
  ip_protocol                  = "tcp"
  from_port                    = local.api_port_min
  to_port                      = local.api_port_max
  referenced_security_group_id = aws_security_group.alb.id
}

# Outbound open: Neon Postgres, Microsoft Graph, Azure Blob, OpenAI, ECR, Valkey...
# (leaves through the NAT gateway; the tasks have no public IPs)
resource "aws_vpc_security_group_egress_rule" "app_all_out" {
  security_group_id = aws_security_group.app.id
  description       = "All outbound"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# ---- Valkey (ElastiCache): only the app tasks may connect ----

resource "aws_security_group" "valkey" {
  name        = "${local.name}-valkey"
  description = "LMS Valkey cache - port 6379 from the app tasks only"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-valkey" }
}

resource "aws_vpc_security_group_ingress_rule" "valkey_from_app" {
  security_group_id            = aws_security_group.valkey.id
  description                  = "Valkey/Redis protocol from the app tasks"
  ip_protocol                  = "tcp"
  from_port                    = 6379
  to_port                      = 6379
  referenced_security_group_id = aws_security_group.app.id
}
# No outbound rule: Valkey only answers connections, it never starts any.
