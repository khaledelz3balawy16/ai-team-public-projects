cd ~/Desktop/LMS_infrastructure/infrastructure
terraform apply s3-endpoint.tfplan
#!/usr/bin/env bash
# Serve lms.kentbusinesscollege.org (and keep lms-aws) on the AWS CloudFront
# distribution, using an ISSUED us-east-1 certificate that covers both names.
# Usage: scripts/cloudfront_live_domain.sh <certificate-arn>
set -euo pipefail

CERT_ARN=${1:?usage: $0 <certificate-arn>}
DIST=E25PMH8T6F7SWU
NAMES='["lms.kentbusinesscollege.org"]'

STATUS=$(aws acm describe-certificate --region us-east-1 --certificate-arn "$CERT_ARN" --query Certificate.Status --output text)
[ "$STATUS" = ISSUED ] || { echo "Certificate is $STATUS, not ISSUED yet - wait for it"; exit 1; }

TMP=$(mktemp -d)
aws cloudfront get-distribution-config --id "$DIST" > "$TMP/current.json"
ETAG=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["ETag"])' "$TMP/current.json")

python3 - "$TMP/current.json" "$TMP/new.json" "$CERT_ARN" "$NAMES" <<'PY'
import json, sys
src, dst, arn, names = sys.argv[1], sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
cfg = json.load(open(src))["DistributionConfig"]
cfg["Aliases"] = {"Quantity": len(names), "Items": names}
cfg["ViewerCertificate"] = {
    "ACMCertificateArn": arn,
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021",
    "CertificateSource": "acm",
    "CloudFrontDefaultCertificate": False,
}
json.dump(cfg, open(dst, "w"))
PY

aws cloudfront update-distribution --id "$DIST" --if-match "$ETAG" \
  --distribution-config "file://$TMP/new.json" \
  --query 'Distribution.[Status,DistributionConfig.Aliases.Items]' --output text
echo "Updated. CloudFront takes a few minutes to deploy the change."
