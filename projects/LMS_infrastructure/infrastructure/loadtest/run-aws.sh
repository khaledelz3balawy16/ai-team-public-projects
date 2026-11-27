#!/usr/bin/env bash
# Runs lms.js from the EC2 load generators (loadgen.tf) instead of this
# machine. Each instance runs PEAK_VUS / <instances> users and signs in once.
# The account comes from the SSM SecureString on the instance; nothing secret
# passes through this script.
#   PEAK_VUS=2000 RAMP=5m HOLD=4m BASE_URL=https://lms-aws.kentbusinesscollege.net ./run-aws.sh
set -euo pipefail
cd "$(dirname "$0")"

: "${BASE_URL:?set BASE_URL}"
: "${PEAK_VUS:?set PEAK_VUS}"
REGION=$(terraform -chdir=.. output -raw aws_region 2>/dev/null || echo eu-west-2)
PARAM=/lms-staging/loadtest/env

mapfile -t ids < <(terraform -chdir=.. output -json loadgen_instance_ids | python3 -c 'import json,sys; print("\n".join(json.load(sys.stdin)))')
[ "${#ids[@]}" -gt 0 ] || { echo "no load generators: terraform apply -var loadgen_enabled=true" >&2; exit 1; }
per=$(( (PEAK_VUS + ${#ids[@]} - 1) / ${#ids[@]} ))

name=$(echo "$BASE_URL" | sed -E 's#https?://##; s#[/.]#_#g')
stamp=$(date +%Y%m%d-%H%M%S)
mkdir -p results
script_b64=$(base64 -w0 lms.js)

remote=$(cat <<EOF
set -e
cd /opt/loadtest
echo '$script_b64' | base64 -d > lms.js
umask 077
aws ssm get-parameter --region $REGION --name $PARAM --with-decryption --query Parameter.Value --output text > loadtest.env
set -a; . ./loadtest.env; set +a
rm -f loadtest.env
ulimit -n 1048576
BASE_URL='$BASE_URL' PEAK_VUS=$per RAMP='${RAMP:-2m}' HOLD='${HOLD:-3m}' k6 run --quiet --no-color --summary-export results/$stamp.json lms.js > results/$stamp.txt 2>&1 || true
tail -c 20000 results/$stamp.txt
EOF
)

params=$(python3 -c 'import json,sys; print(json.dumps({"commands": [sys.argv[1]], "executionTimeout": ["3600"]}))' "$remote")
cmd=$(aws ssm send-command --region $REGION --instance-ids "${ids[@]}" --document-name AWS-RunShellScript \
  --parameters "$params" --timeout-seconds 600 --query Command.CommandId --output text)
echo "started $stamp on ${#ids[@]} instances x $per users (command $cmd)"

for id in "${ids[@]}"; do
  until s=$(aws ssm get-command-invocation --region $REGION --command-id "$cmd" --instance-id "$id" --query Status --output text 2>/dev/null) \
        && [[ "$s" != Pending && "$s" != InProgress && "$s" != Delayed ]]; do sleep 20; done
  out="results/${name}-${stamp}-${id}"
  aws ssm get-command-invocation --region $REGION --command-id "$cmd" --instance-id "$id" \
    --query StandardOutputContent --output text > "$out.txt"
  # Summary JSON, fetched separately (small)
  jcmd=$(aws ssm send-command --region $REGION --instance-ids "$id" --document-name AWS-RunShellScript \
    --parameters "{\"commands\":[\"cat /opt/loadtest/results/$stamp.json\"]}" --query Command.CommandId --output text)
  until j=$(aws ssm get-command-invocation --region $REGION --command-id "$jcmd" --instance-id "$id" --query Status --output text 2>/dev/null) \
        && [[ "$j" != Pending && "$j" != InProgress ]]; do sleep 3; done
  aws ssm get-command-invocation --region $REGION --command-id "$jcmd" --instance-id "$id" \
    --query StandardOutputContent --output text > "$out.json"
  echo "$id: $s -> $out.txt"
done
