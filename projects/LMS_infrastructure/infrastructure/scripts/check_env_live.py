'Is the website running with the settings in backend/.env?\n\nChecks, without printing any value:\n  1. .env vs AWS Secrets Manager (CHANGE_ME): keys missing, extra or\n     with a different value (compared by hash), parsed exactly like\n     env_to_tfvars.py does\n  2. every ECS service: rollout finished, and every running task started\n     AFTER the secret last changed (tasks read settings only at start-up)\n\nUsage: python3 -I scripts/check_env_live.py [path/to/.env]\nSettings that ecs.tf sets itself (app_environment: FRONTEND_URL, hosts,\ncallbacks, cache...) override .env and are listed separately.\n'
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from env_to_tfvars import parse  # noqa: E402  same parser as the upload

REGION = "eu-west-2"
SECRET = 'CHANGE_ME'
CLUSTER = "lms-staging-cluster"
ENV_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Desktop/LMS_v2/backend/.env")


def aws(*args):
    out = subprocess.run(["aws", "--region", REGION, *args, "--output", "json"],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def when(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


local, _ = parse(ENV_PATH)
secret = aws("secretsmanager", 'CHANGE_ME', "--secret-id", SECRET)
remote = json.loads(secret["SecretString"])
changed_at = when(aws("secretsmanager", 'CHANGE_ME', "--secret-id", SECRET)["LastChangedDate"])

# Names ecs.tf sets itself (they win over .env on AWS)
services = [a.rsplit("/", 1)[1] for a in aws("ecs", "list-services", "--cluster", CLUSTER)["serviceArns"]]
described = aws("ecs", "describe-services", "--cluster", CLUSTER, "--services", *services)["services"]
td = aws("ecs", "describe-task-definition", "--task-definition", described[0]["taskDefinition"])
plain = {e["name"] for e in td["taskDefinition"]["containerDefinitions"][0].get("environment", [])}

missing = sorted(k for k in local if k not in remote and k not in plain)
extra = sorted(k for k in remote if k not in local)
different = sorted(k for k in local if k in remote and digest(local[k]) != digest(remote[k]))
overridden = sorted(k for k in local if k in plain)

print(f"1. .env ({len(local)} settings) vs AWS secret ({len(remote)} settings), secret last changed {changed_at:%Y-%m-%d %H:%M} UTC")
print(f"   different value : {', '.join(different) or 'none'}")
print(f"   only in .env    : {', '.join(missing) or 'none'}   (not uploaded yet)")
print(f"   only in AWS     : {', '.join(extra) or 'none'}")
print(f"   set by ecs.tf instead of .env: {', '.join(overridden) or 'none'}")
in_sync = not (different or missing)

print("2. Services (tasks read settings only when they start):")
all_live = True
for s in sorted(described, key=lambda x: x["serviceName"]):
    arns = aws("ecs", "list-tasks", "--cluster", CLUSTER, "--service-name", s["serviceName"],
               "--desired-status", "RUNNING")["taskArns"]
    tasks = aws("ecs", "describe-tasks", "--cluster", CLUSTER, "--tasks", *arns)["tasks"] if arns else []
    old = [t for t in tasks if "startedAt" in t and when(t["startedAt"]) < changed_at]
    rollout = s["deployments"][0].get("rolloutState", "?")
    ok = rollout == "COMPLETED" and not old and tasks
    all_live &= bool(ok)
    print(f"   {'OK ' if ok else 'WAIT'} {s['serviceName']:<15} rollout={rollout:<11} "
          f"tasks={len(tasks)}  started before the change={len(old)}")

print()
if in_sync and all_live:
    print("RESULT: the website is running with your .env settings.")
elif not in_sync:
    print("RESULT: AWS doesn't match your .env yet - run env_to_tfvars.py, terraform plan and apply.")
else:
    print("RESULT: AWS has your settings, but some servers haven't restarted yet - check again in a few minutes.")
