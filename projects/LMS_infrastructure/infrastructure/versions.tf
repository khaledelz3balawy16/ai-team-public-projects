# ------------------------------------------------------------
# LMS on AWS - Terraform and provider setup
# Region: eu-west-2 (London), next to the Neon databases.
# ------------------------------------------------------------

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # State is local and git-ignored: the London stack uses the "london"
  # workspace (terraform.tfstate.d/london/); the default workspace holds the
  # old Stockholm stack in the previous account. Move it to an S3 backend
  # before more than one person runs Terraform.
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# CloudFront only accepts certificates from us-east-1, so the certificate
# is created with this second provider. Nothing else is created there.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
