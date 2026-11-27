# ------------------------------------------------------------
# Read-only access to course files for the developers' local backends and
# the dev-lms server (outside AWS, so they can't use the task role).
#
# Only the course-material folder: the files bucket also holds contracts,
# enrolment documents, evidence and saved emails, which a dev copy must
# not read. Add a folder to dev_files_read_prefixes only when dev needs it.
#
# The access key is NOT created here (it would sit in Terraform state):
# create it in the IAM console for this user, hand it over privately, keep
# it out of git/.env files, and rotate it (delete the old key) regularly.
# ------------------------------------------------------------

variable "dev_files_read_prefixes" {
  description = "Folders (S3 key prefixes, ending in /) the dev backends may read from the files bucket"
  type        = list(string)
  default     = ["kbcdocs/curriculum-uploads/"]

  validation {
    condition     = alltrue([for p in var.dev_files_read_prefixes : endswith(p, "/") && !startswith(p, "/")])
    error_message = "Each prefix must be a folder path like \"kbcdocs/curriculum-uploads/\"."
  }
}

resource "aws_iam_user" "dev_files_reader" {
  name = "${local.name}-dev-files-reader"
  tags = { Purpose = "Read-only course files for local and dev-lms backends" }
}

resource "aws_iam_user_policy" "dev_files_reader" {
  name = "read-course-files"
  user = aws_iam_user.dev_files_reader.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadCourseFiles"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = [for p in var.dev_files_read_prefixes : "${aws_s3_bucket.files.arn}/${p}*"]
      },
      {
        # Lets a missing file come back as "not found" (404) instead of
        # "access denied" (403); listing stays inside the same folders
        Sid      = "ListCourseFolders"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.files.arn
        Condition = {
          StringLike = { "s3:prefix" = [for p in var.dev_files_read_prefixes : "${p}*"] }
        }
      },
    ]
  })
}

output "dev_files_reader_user" {
  description = "IAM user to create the dev access key for (IAM console > Users > this user > Security credentials)"
  value       = aws_iam_user.dev_files_reader.name
}
