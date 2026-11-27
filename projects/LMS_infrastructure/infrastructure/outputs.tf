output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "app_subnet_ids" {
  value = aws_subnet.app[*].id
}

output "data_subnet_ids" {
  value = aws_subnet.data[*].id
}

output "nat_public_ips" {
  description = "All outbound traffic from the app leaves from these IPs (useful for allow-lists, e.g. Neon IP allow)"
  value       = aws_eip.nat[*].public_ip
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "valkey_primary_endpoint" {
  description = "Write endpoint; app URL is rediss://<this>:6379"
  value       = aws_elasticache_replication_group.valkey.primary_endpoint_address
}

output "valkey_reader_endpoint" {
  value = aws_elasticache_replication_group.valkey.reader_endpoint_address
}

output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "app_secret_name" {
  description = "Filled from secrets.auto.tfvars (generated from backend/.env)"
  value       = aws_secretsmanager_secret.app.name
}

output "jobs_queue_url" {
  value = aws_sqs_queue.jobs.url
}

output "api_routing" {
  description = "URL paths -> service/port, as configured on the load balancer"
  value       = { for k, v in local.api_services : k => "${join(", ", v.paths)} -> :${v.port}" }
}

output "ecs_services" {
  description = "ECS service name -> container port"
  value       = { for k, v in local.api_services : aws_ecs_service.api[k].name => v.port }
}

output "site_url" {
  description = "Open the LMS here"
  value       = local.site_url
}

output "cloudfront_url" {
  value = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "dns_record" {
  description = "Add this record in Hostinger DNS"
  value = {
    type   = "CNAME"
    name   = split(".", var.domain_name)[0] # Hostinger adds the domain itself
    target = aws_cloudfront_distribution.main.domain_name
  }
}

output "certificate_validation_record" {
  description = "Add this record in Hostinger DNS once, so AWS can issue the certificate"
  value = [for o in aws_acm_certificate.site.domain_validation_options : {
    type   = o.resource_record_type
    name   = trimsuffix(trimsuffix(trimsuffix(o.resource_record_name, "."), ".kentbusinesscollege.org"), ".kentbusinesscollege.net")
    target = o.resource_record_value
  }]
}

output "cloudfront_distribution_id" {
  description = "Used to invalidate the cache after a frontend upload"
  value       = aws_cloudfront_distribution.main.id
}

output "frontend_bucket" {
  description = "Upload frontend/out here"
  value       = aws_s3_bucket.frontend.bucket
}

output "aws_region" {
  value = var.aws_region
}
