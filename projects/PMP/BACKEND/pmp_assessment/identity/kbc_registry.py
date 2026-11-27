from ..models import KBCPmpLearnerRegistry, normalize_email

def find_registry_record(email):
    return KBCPmpLearnerRegistry.objects.filter(normalized_email=normalize_email(email), is_active=True).first()

def sync_kbc_learner(*args, **kwargs):
    raise NotImplementedError("LearningOS sync is intentionally not connected in standalone PMP.")
