# ------------------------------------------------------------
# Load generator (off by default): EC2 instances that runs k6 for tests
# too large for a laptop (2000+ users). It sits in a public subnet so its
# traffic reaches CloudFront through the internet gateway, not the NAT.
# No inbound ports: commands go through SSM. The test account is read from
# the SecureString parameter var.loadgen_credentials_parameter at run time.
#
#   terraform apply -var loadgen_enabled=true    # start it
#   terraform apply                              # remove it again
# ------------------------------------------------------------

variable "loadgen_enabled" {
  description = "Create the k6 load generator instance (billed per hour while it exists)"
  type        = bool
  default     = false
}

variable "loadgen_instance_type" {
  description = "Load generator size; EC2 has its own vCPU limit, separate from Fargate"
  type        = string
  default     = "m7i-flex.large"
}

variable "loadgen_count" {
  description = "Load generator instances; each runs its share of the virtual users"
  type        = number
  default     = 2
}

variable "loadgen_credentials_parameter" {
  description = "SSM SecureString holding loadtest.env (LOADTEST_EMAIL=..., LOADTEST_PASSWORD=...)"
  type        = string
  default     = "/lms-staging/loadtest/env"
}

variable "k6_version" {
  description = "k6 release installed on the load generator"
  type        = string
  default     = "v1.3.0"
}

data "aws_ssm_parameter" "al2023" {
  count = var.loadgen_enabled ? 1 : 0
  name  = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_iam_role" "loadgen" {
  count = var.loadgen_enabled ? 1 : 0
  name  = "${local.name}-loadgen"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "loadgen_ssm" {
  count      = var.loadgen_enabled ? 1 : 0
  role       = aws_iam_role.loadgen[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "loadgen_credentials" {
  count = var.loadgen_enabled ? 1 : 0
  name  = "read-loadtest-credentials"
  role  = aws_iam_role.loadgen[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "ssm:GetParameter"
      Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.loadgen_credentials_parameter}"
    }]
  })
}

resource "aws_iam_instance_profile" "loadgen" {
  count = var.loadgen_enabled ? 1 : 0
  name  = "${local.name}-loadgen"
  role  = aws_iam_role.loadgen[0].name
}

resource "aws_security_group" "loadgen" {
  count       = var.loadgen_enabled ? 1 : 0
  name        = "${local.name}-loadgen"
  description = "k6 load generator: outbound only"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "loadgen" {
  count                       = var.loadgen_enabled ? var.loadgen_count : 0
  ami                         = data.aws_ssm_parameter.al2023[0].value
  instance_type               = var.loadgen_instance_type
  subnet_id                   = aws_subnet.public[count.index % length(aws_subnet.public)].id
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.loadgen[0].id]
  iam_instance_profile        = aws_iam_instance_profile.loadgen[0].name

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  # k6 plus OS limits for thousands of connections
  user_data = <<-EOT
    #!/bin/bash
    set -euxo pipefail
    curl -fsSL https://github.com/grafana/k6/releases/download/${var.k6_version}/k6-${var.k6_version}-linux-amd64.tar.gz | tar -xz -C /tmp
    install /tmp/k6-${var.k6_version}-linux-amd64/k6 /usr/local/bin/k6
    cat > /etc/sysctl.d/99-loadtest.conf <<'EOF'
    net.ipv4.ip_local_port_range = 1024 65535
    net.ipv4.tcp_tw_reuse = 1
    net.core.somaxconn = 65535
    EOF
    sysctl --system
    echo '* - nofile 1048576' > /etc/security/limits.d/99-loadtest.conf
    mkdir -p /opt/loadtest/results
  EOT

  tags = { Name = "${local.name}-loadgen-${count.index + 1}" }
}

output "loadgen_instance_ids" {
  description = "Load generator instances (when loadgen_enabled), for aws ssm send-command"
  value       = aws_instance.loadgen[*].id
}
