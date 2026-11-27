# ------------------------------------------------------------
# ECR (diagram: "ECR - Docker images") - registry for the backend image
# ------------------------------------------------------------

resource "aws_ecr_repository" "backend" {
  name                 = "${local.name}-backend"
  image_tag_mutability = "MUTABLE" # :latest is re-pushed on each deploy
  force_delete         = true      # staging: allow terraform destroy with images inside

  # Free vulnerability scan of every pushed image
  image_scanning_configuration {
    scan_on_push = true
  }
}

# Keep the 20 newest images (each deploy pushes :latest + :<commit>)
resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 20 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 20
      }
      action = { type = "expire" }
    }]
  })
}
