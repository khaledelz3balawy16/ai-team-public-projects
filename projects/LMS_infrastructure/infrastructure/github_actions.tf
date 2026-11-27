# ------------------------------------------------------------
# CI/CD: GitHub Actions deploys LMS_v2's main branch to this stack.
# GitHub signs in with OpenID Connect (short-lived credentials per run),
# so no AWS access keys are stored in GitHub.
# The role can only: push the backend image, restart the API services,
# upload the frontend and clear the CloudFront cache. Terraform stays the
# owner of everything else (task sizes, scaling, settings).
# ------------------------------------------------------------

variable "github_repository" {
  description = "GitHub repo (owner/name) allowed to deploy; empty = no CI/CD role"
  type        = string
  default     = "aiteamKBC/LMS_v2"
}

variable "github_deploy_branch" {
  description = "Only workflow runs on this branch may deploy"
  type        = string
  default     = "main"
}

# GitHub sends this repo as "owner@<owner id>/name@<repo id>" (immutable IDs,
# so a renamed or re-created repo can't take over). Seen in CloudTrail
# AssumeRoleWithWebIdentity events; empty = names only.
variable "github_repository_with_ids" {
  description = "The repo as GitHub's OIDC subject spells it with IDs"
  type        = string
  default     = "aiteamKBC@223314142/LMS_v2@1339229648"
}

variable "github_deploy_environment" {
  description = "GitHub environment used by the deploy job (deploy-aws.yml)"
  type        = string
  default     = "aws-staging"
}

locals {
  github_deploy = var.github_repository != ""
}

# One per account: lets IAM trust tokens issued by GitHub Actions.
# AWS checks GitHub's certificate itself; the thumbprint is not used.
resource "aws_iam_openid_connect_provider" "github" {
  count = local.github_deploy ? 1 : 0

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "github_assume" {
  count = local.github_deploy ? 1 : 0

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github[0].arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    # Only this one repo: runs on main, or jobs using the deploy environment
    # (a job with `environment:` gets ":environment:<name>" instead of
    # ":ref:..."; that environment must only allow the main branch, set in
    # GitHub > Settings > Environments > Deployment branches)
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values = flatten([
        for repo in compact([var.github_repository, var.github_repository_with_ids]) : [
          "repo:${repo}:ref:refs/heads/${var.github_deploy_branch}",
          "repo:${repo}:environment:${var.github_deploy_environment}",
        ]
      ])
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  count = local.github_deploy ? 1 : 0

  name                 = "${local.name}-github-deploy"
  assume_role_policy   = data.aws_iam_policy_document.github_assume[0].json
  max_session_duration = 3600
}

resource "aws_iam_role_policy" "github_deploy" {
  count = local.github_deploy ? 1 : 0

  name = "deploy"
  role = aws_iam_role.github_deploy[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EcrLogin"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*" # this action has no resource-level permissions
      },
      {
        Sid    = "PushBackendImage"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload",
          "ecr:PutImage", "ecr:DescribeImages",
        ]
        Resource = aws_ecr_repository.backend.arn
      },
      {
        Sid      = "RestartApiServices"
        Effect   = "Allow"
        Action   = ["ecs:UpdateService", "ecs:DescribeServices"]
        Resource = "arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:service/${aws_ecs_cluster.main.name}/*"
      },
      {
        Sid      = "ListApiServices"
        Effect   = "Allow"
        Action   = "ecs:ListServices"
        Resource = "*" # scoped by the cluster argument; no resource-level permissions
        Condition = {
          ArnEquals = { "ecs:cluster" = aws_ecs_cluster.main.arn }
        }
      },
      # Calendar schema gate (.github/ci/calendar_release.py): reads the
      # curriculum-api/night-api task definitions, registers a one-off copy
      # (family "<service family>-calendar-gate") with the candidate image and
      # runs it once in this cluster to apply the additive calendar migrations
      # before the image is promoted.
      {
        Sid      = "CalendarGateReadDefinitions"
        Effect   = "Allow"
        Action   = ["ecs:DescribeTaskDefinition", "ecs:RegisterTaskDefinition"]
        Resource = "*" # neither action supports resource-level permissions
      },
      {
        Sid      = "CalendarGateRunTask"
        Effect   = "Allow"
        Action   = "ecs:RunTask"
        Resource = [for s in ["curriculum-api", "night-api"] : "arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:task-definition/${local.name}-${s}-calendar-gate:*"]
        Condition = {
          ArnEquals = { "ecs:cluster" = aws_ecs_cluster.main.arn }
        }
      },
      {
        Sid      = "CalendarGateWatchTask"
        Effect   = "Allow"
        Action   = ["ecs:DescribeTasks", "ecs:StopTask"]
        Resource = "arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:task/${aws_ecs_cluster.main.name}/*"
      },
      {
        Sid      = "CalendarGatePassTaskRoles"
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = [aws_iam_role.task_execution.arn, aws_iam_role.task.arn]
        Condition = {
          StringEquals = { "iam:PassedToService" = "ecs-tasks.amazonaws.com" }
        }
      },
      {
        Sid      = "FrontendBucketList"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.frontend.arn
      },
      {
        Sid      = "FrontendBucketFiles"
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:DeleteObject", "s3:GetObject"]
        Resource = "${aws_s3_bucket.frontend.arn}/*"
      },
      {
        Sid      = "ClearCdnCache"
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation", "cloudfront:GetInvalidation"]
        Resource = aws_cloudfront_distribution.main.arn
      },
      {
        # Post-deploy watch: load balancer error rate and response time
        Sid      = "ReadMetrics"
        Effect   = "Allow"
        Action   = ["cloudwatch:GetMetricData"]
        Resource = "*" # no resource-level permissions for this action
      },
    ]
  })
}

# ---- Values to put in the GitHub repo (Settings > Secrets and variables >
# Actions > Variables). None of them is secret. ----

output "github_actions_variables" {
  description = "Add these as Actions *variables* in the LMS_v2 GitHub repo"
  value = local.github_deploy ? {
    AWS_DEPLOY_ROLE_ARN        = aws_iam_role.github_deploy[0].arn
    AWS_REGION                 = var.aws_region
    ECR_REPOSITORY             = aws_ecr_repository.backend.name
    ECS_CLUSTER                = aws_ecs_cluster.main.name
    IMAGE_TAG                  = var.image_tag
    FRONTEND_BUCKET            = aws_s3_bucket.frontend.bucket
    CLOUDFRONT_DISTRIBUTION_ID = aws_cloudfront_distribution.main.id
    SITE_URL                   = local.site_url
    ALB_METRIC_ID              = aws_lb.main.arn_suffix # LoadBalancer dimension for the post-deploy watch
  } : null
}
