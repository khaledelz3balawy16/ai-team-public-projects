# ------------------------------------------------------------
# SQS (diagram: "SQS - Celery job queue")
# Created now so the architecture is in place; the app does not use a job
# queue yet (phase 1). Messages that fail 5 times move to the dead-letter
# queue instead of retrying forever.
# ------------------------------------------------------------

resource "aws_sqs_queue" "jobs_dlq" {
  name                      = "${local.name}-jobs-dlq"
  message_retention_seconds = 1209600 # 14 days to inspect failed jobs
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "jobs" {
  name                       = "${local.name}-jobs"
  visibility_timeout_seconds = 900    # a worker has 15 min before a job is retried
  message_retention_seconds  = 345600 # 4 days
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.jobs_dlq.arn
    maxReceiveCount     = 5
  })
}
