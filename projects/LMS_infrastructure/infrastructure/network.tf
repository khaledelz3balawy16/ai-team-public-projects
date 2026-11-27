# ------------------------------------------------------------
# Network (diagram: "VPC"). Per availability zone:
#   public subnet       - load balancer and NAT gateway
#   private app subnet  - ECS Fargate tasks (no public IPs)
#   private data subnet - ElastiCache Valkey (no internet route at all)
# ------------------------------------------------------------

locals {
  name = "${var.project}-${var.environment}" # e.g. lms-staging

  # Carve /24 subnets out of the VPC range:
  #   10.20.0-2.x    public (one /24 per zone)
  #   10.20.10-12.x  app
  #   10.20.20-22.x  data
  public_cidrs = [for i, _ in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i)]
  app_cidrs    = [for i, _ in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, 10 + i)]
  data_cidrs   = [for i, _ in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, 20 + i)]
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true # needed for ECR/ElastiCache endpoint names

  tags = { Name = local.name }
}

# Door to the internet for the public subnets
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = local.name }
}

# ---- Subnets ----

resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  availability_zone       = var.availability_zones[count.index]
  cidr_block              = local.public_cidrs[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "${local.name}-public-${substr(var.availability_zones[count.index], -1, 1)}", Tier = "public" }
}

resource "aws_subnet" "app" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  availability_zone = var.availability_zones[count.index]
  cidr_block        = local.app_cidrs[count.index]

  tags = { Name = "${local.name}-app-${substr(var.availability_zones[count.index], -1, 1)}", Tier = "app" }
}

resource "aws_subnet" "data" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  availability_zone = var.availability_zones[count.index]
  cidr_block        = local.data_cidrs[count.index]

  tags = { Name = "${local.name}-data-${substr(var.availability_zones[count.index], -1, 1)}", Tier = "data" }
}

# ---- NAT gateways: outbound internet for the private app subnets ----
# (Neon, Microsoft Graph, OpenAI, Azure Blob, ECR...). One per zone when
# var.nat_per_az, so a zone failure doesn't cut the others off; otherwise
# one in zone A. Each is billed per hour even when idle.

locals {
  nat_count = var.nat_per_az ? length(var.availability_zones) : 1
}

resource "aws_eip" "nat" {
  count  = local.nat_count
  domain = "vpc"
  tags   = { Name = "${local.name}-nat-${substr(var.availability_zones[count.index], -1, 1)}" }
}

resource "aws_nat_gateway" "main" {
  count         = local.nat_count
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = { Name = "${local.name}-${substr(var.availability_zones[count.index], -1, 1)}" }

  depends_on = [aws_internet_gateway.main]
}

# The original single NAT (zone A) becomes index 0, keeping its IP
moved {
  from = aws_eip.nat
  to   = aws_eip.nat[0]
}

moved {
  from = aws_nat_gateway.main
  to   = aws_nat_gateway.main[0]
}

# ---- Route tables ----

# Public: 0.0.0.0/0 -> internet gateway
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${local.name}-public" }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# App: 0.0.0.0/0 -> the NAT gateway in the same zone (outbound only,
# nothing can connect in). With a single NAT every zone uses zone A's.
resource "aws_route_table" "app" {
  count  = local.nat_count
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = { Name = "${local.name}-app-${substr(var.availability_zones[count.index], -1, 1)}" }
}

moved {
  from = aws_route_table.app
  to   = aws_route_table.app[0]
}

resource "aws_route_table_association" "app" {
  count          = length(aws_subnet.app)
  subnet_id      = aws_subnet.app[count.index].id
  route_table_id = aws_route_table.app[var.nat_per_az ? count.index : 0].id
}

# Data: local VPC traffic only - Valkey never needs the internet
resource "aws_route_table" "data" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name}-data" }
}

resource "aws_route_table_association" "data" {
  count          = length(aws_subnet.data)
  subnet_id      = aws_subnet.data[count.index].id
  route_table_id = aws_route_table.data.id
}

# S3 gateway endpoint (free): S3 traffic from the private subnets - the app's
# file reads/writes and the ECR image layers every deploy pulls (~0.3 GB per
# task) - goes straight to S3 instead of through the NAT gateway, which
# charges per GB.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = concat(aws_route_table.app[*].id, aws_route_table.data[*].id)
  tags              = { Name = "${local.name}-s3" }
}
