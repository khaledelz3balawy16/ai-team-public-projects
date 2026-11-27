def resolve_lms_identity(*args, **kwargs):
    raise NotImplementedError("Future LMS identity resolution adapter placeholder.")

def link_lms_user(profile, *, future_lms_user_id=None, future_lms_learner_id=None):
    profile.future_lms_user_id = future_lms_user_id
    profile.future_lms_learner_id = future_lms_learner_id
    return profile
