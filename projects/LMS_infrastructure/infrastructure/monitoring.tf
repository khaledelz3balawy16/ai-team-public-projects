# ------------------------------------------------------------
# Alerts. One SNS topic; var.alert_email (empty = no subscription, the
# alarms still show in the CloudWatch console) gets an email per alarm.
# AWS sends a confirmation email first: the link in it must be clicked.
# ------------------------------------------------------------

variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications (empty = none)"
  type        = string
  default     = ""
}

resource "aws_sns_topic" "alerts" {
  name = "${local.name}-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Valkey memory: the app's caches must stay well below maxmemory; near it,
# Valkey evicts entries and the app falls back to the database (11 Nov 2026:
# stale curriculum generations filled 99.9%). One alarm per node.
resource "aws_cloudwatch_metric_alarm" "valkey_memory" {
  for_each = toset(aws_elasticache_replication_group.valkey.member_clusters)

  alarm_name          = "${each.value}-memory-high"
  alarm_description   = "Valkey memory above 70% of maxmemory for 10 minutes: caches are growing towards eviction"
  namespace           = "AWS/ElastiCache"
  metric_name         = "DatabaseMemoryUsagePercentage"
  dimensions          = { CacheClusterId = each.value }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  threshold           = 70
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

# Any eviction means the cache is full and entries are being thrown away
resource "aws_cloudwatch_metric_alarm" "valkey_evictions" {
  for_each = toset(aws_elasticache_replication_group.valkey.member_clusters)

  alarm_name          = "${each.value}-evictions"
  alarm_description   = "Valkey is evicting keys (memory full)"
  namespace           = "AWS/ElastiCache"
  metric_name         = "Evictions"
  dimensions          = { CacheClusterId = each.value }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
