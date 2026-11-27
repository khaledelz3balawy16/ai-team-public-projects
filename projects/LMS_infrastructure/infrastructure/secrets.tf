# ------------------------------------------------------------
# Secrets Manager (diagram: "Secrets Manager")
# One secret holding the app's settings as JSON key/value pairs, with the
# same names as backend/.env. The values come from var.app_secrets
# (secrets.auto.tfvars, git-ignored) and are sent as a write-only value,
# so they are NOT saved in terraform.tfstate.
# ------------------------------------------------------------

resource "aws_secretsmanager_secret" "app" {
  name        = "${local.name}/app"
  description = "LMS staging app settings (from backend/.env)"

  # Staging: allow immediate re-creation after terraform destroy
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = CHANGE_ME

  # Write-only: Terraform can't see the current value, so it only re-sends
  # when app_secrets_version changes
  secret_string_wo         = jsonencode(var.app_secrets)
  secret_string_wo_version = CHANGE_ME
}
