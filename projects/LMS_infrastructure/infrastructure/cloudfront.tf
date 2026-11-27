# ------------------------------------------------------------
# CloudFront (diagram: "CloudFront - HTTPS entry point")
# One domain for the whole site, like the VPS proxy:
#   var.backend_paths (API, chat WebSocket, admin) -> load balancer
#   everything else                                -> React app in S3
# The frontend calls the API with relative paths, so no CORS is needed.
# ------------------------------------------------------------

# AWS-managed policies
data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

# Forwards every header (incl. Host and the WebSocket upgrade), cookie and
# query string, so Django sees the request as the browser sent it
data "aws_cloudfront_origin_request_policy" "all_viewer" {
  name = "Managed-AllViewer"
}

# Certificate for domain_name, checked by DNS: add the record from the
# certificate_validation_record output in Hostinger once
resource "aws_acm_certificate" "site" {
  provider                  = aws.us_east_1
  domain_name               = var.domain_name
  subject_alternative_names = var.certificate_extra_names
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${local.name}-frontend"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# React routes (/learner/home, ...) have no file in S3: serve index.html and
# let the app's router handle them. Only runs for S3, so API 404s stay intact.
resource "aws_cloudfront_function" "spa_routes" {
  name    = "${local.name}-spa-routes"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOT
    function handler(event) {
      var request = event.request;
      var lastSegment = request.uri.split('/').pop();
      if (lastSegment.indexOf('.') === -1) {
        request.uri = '/index.html';
      }
      return request;
    }
  EOT
}

locals {
  s3_origin_id  = "frontend-s3"
  alb_origin_id = "backend-alb"
}

locals {
  certificate_issued = aws_acm_certificate.site.status == "ISSUED"
}

resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  comment             = "${local.name} - LMS frontend + API"
  default_root_object = "index.html"
  aliases             = var.attach_domain ? [var.domain_name] : []
  price_class         = "PriceClass_100" # edge locations in Europe and North America
  http_version        = "http2and3"

  origin {
    origin_id                = local.s3_origin_id
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }

  origin {
    origin_id   = local.alb_origin_id
    domain_name = aws_lb.main.dns_name

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only" # the load balancer has no certificate yet
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 60
    }
  }

  # Everything not matched below: the React app
  default_cache_behavior {
    target_origin_id       = local.s3_origin_id
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = data.aws_cloudfront_cache_policy.optimized.id
    compress               = true

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_routes.arn
    }
  }

  # Backend paths: never cached, everything forwarded
  dynamic "ordered_cache_behavior" {
    for_each = var.backend_paths
    content {
      path_pattern             = ordered_cache_behavior.value
      target_origin_id         = local.alb_origin_id
      viewer_protocol_policy   = "redirect-to-https"
      allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      cached_methods           = ["GET", "HEAD"]
      cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
      origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer.id
      compress                 = true
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # The certificate goes on as soon as it is ISSUED (an alias can only be
  # moved here from another distribution once it is), https://<domain_name>
  # once attach_domain is on; https://<id>.cloudfront.net works either way
  viewer_certificate {
    acm_certificate_arn            = local.certificate_issued ? aws_acm_certificate.site.arn : null
    ssl_support_method             = local.certificate_issued ? "sni-only" : null
    minimum_protocol_version       = local.certificate_issued ? "TLSv1.2_2021" : null
    cloudfront_default_certificate = !local.certificate_issued
  }
}
