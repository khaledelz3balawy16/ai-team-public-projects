# ------------------------------------------------------------
# File storage for uploads (replacing Azure Blob Storage).
# One private bucket in London. Objects keep their Azure names under
#   <azure account>/<container>/<blob name>
# so database references don't change. Downloads go out as short-lived
# presigned links signed by the app's task role; nothing is public.
#
# The app reads (set for every service in ecs.tf / worker.tf):
#   STORAGE_BACKEND    azure | s3   (var.storage_backend; flip to s3 only
#                                    after the files are copied)
#   AWS_S3_STORAGE_BUCKET  this bucket
#   AWS_S3_STORAGE_REGION  var.aws_region
# ------------------------------------------------------------

variable "storage_backend" {
  description = "Where the app stores uploads: s3 (since 8 Nov 2026) or azure (rollback: Azure files are kept unchanged)"
  type        = string
  default     = "s3"
  validation {
    condition     = contains(["azure", "s3"], var.storage_backend)
    error_message = "storage_backend must be azure or s3."
  }
}

resource "aws_s3_bucket" "files" {
  bucket = "${local.name}-files-${data.aws_caller_identity.current.account_id}"

  # Learner evidence and documents: never deleted by terraform destroy
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "files" {
  bucket                  = aws_s3_bucket.files.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "files" {
  bucket = aws_s3_bucket.files.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "files" {
  bucket = aws_s3_bucket.files.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Overwritten or deleted files stay recoverable for 30 days
resource "aws_s3_bucket_versioning" "files" {
  bucket = aws_s3_bucket.files.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "files" {
  bucket = aws_s3_bucket.files.id

  rule {
    id     = "old-versions-and-failed-uploads"
    status = "Enabled"
    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.files]
}

# HTTPS only
data "aws_iam_policy_document" "files_bucket" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.files.arn, "${aws_s3_bucket.files.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "files" {
  bucket     = aws_s3_bucket.files.id
  policy     = data.aws_iam_policy_document.files_bucket.json
  depends_on = [aws_s3_bucket_public_access_block.files]
}

# The learner pages read PDFs and Office files straight from their signed
# links with fetch() (frontend api/pdfResource.ts) to show previews; the
# browser only allows that if the bucket names the site as an allowed origin.
# Read-only: uploads still go through the app.
variable "files_extra_cors_origins" {
  description = "Other sites whose browser pages may read files from the files bucket (CORS only: every file still needs a signed link from the app)"
  type        = list(string)
  default = [
    "http://localhost:3000", # local frontend (vite dev server)
    "http://dev-lms.kentbusinesscollege.net",
    "https://dev-lms.kentbusinesscollege.net",
  ]
}

resource "aws_s3_bucket_cors_configuration" "files" {
  bucket = aws_s3_bucket.files.id
  cors_rule {
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = concat([for h in local.site_hosts : "https://${h}"], var.files_extra_cors_origins)
    allowed_headers = ["*"]
    expose_headers  = ["Content-Type", "Content-Length", "Content-Disposition", "Content-Range", "Accept-Ranges", "ETag"]
    max_age_seconds = 3600
  }
}

# The running app (task role): read, write, delete and list its files only
resource "aws_iam_role_policy" "task_files" {
  name = "app-files"
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Objects"
        Effect = "Allow"
        Action = [
          "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
          "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts",
        ]
        Resource = "${aws_s3_bucket.files.arn}/*"
      },
      {
        Sid      = "Bucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucketLocation"]
        Resource = aws_s3_bucket.files.arn
      },
    ]
  })
}

output "files_bucket" {
  description = "S3 bucket for uploaded files (AWS_S3_STORAGE_BUCKET)"
  value       = aws_s3_bucket.files.bucket
}
