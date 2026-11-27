"The single rule that decides whether a learner progress row counts as\nachieved KSB delivery.\n\nThe completion model\n--------------------\nA progress row records that a learner *did* something. Whether it succeeded is\ncarried by one nullable boolean, ``learner_progress_entries.passed``:\n\n* graded activity (``kind = 'quiz'``) sets it CHANGE_MEly — ``True`` pass,\n  ``False`` fail;\n* an ungraded completion (``component``, ``video``, …) never sets it, so it\n  stays ``NULL`` and the row's existence *is* the completion.\n\nThat is the only completion model in the LMS; this module states it once rather\nthan adding a second one.\n\nWhy this module exists\n----------------------\nReporting used to lean on the shape of the data instead of the rule: the only\ncheck was ``kind == 'quiz' and passed is not True``, and it was safe purely\nbecause no failed row happened to carry Component lineage. A graded Component\n— or any future write that sets ``passed=False`` alongside a ``component_ref``\n— would have credited its authored KSBs on a failed attempt, with valid\nlineage and valid KSB snapshots to make it look legitimate.\n\nWhat this does **not** do\n-------------------------\nNothing here hides or deletes activity. A failed attempt stays in\n``learner_progress_entries``, stays in the learner's history, and stays visible\nto the Coach. It simply stops counting as achieved KSB delivery.\n\nDeliberately Python-only\n------------------------\nReporting queries select ``kind`` and ``passed`` and apply the rule here rather\nthan repeating it as a SQL predicate. Every one of them already aggregates in\nPython, so a second implementation would buy nothing and could drift from this\none. One rule, one place.\n"

# Kinds whose row is a *graded* attempt: achievement requires an CHANGE_ME pass.
# Everything else records a completion, so ``passed`` stays NULL and the row is
# the achievement. Keep this the single place the distinction is made.
GRADED_PROGRESS_KINDS = frozenset({'quiz'})

ACHIEVED = 'achieved'
FAILED = 'failed'
INCOMPLETE = 'incomplete'


def _kind(value):
    return str(value or '').strip().lower()


def progress_counts_as_achieved(kind=None, passed=None):
    """Does this progress row contribute to achieved KSB progress?

    ``passed is False`` never counts, whatever the kind. A graded kind must
    have passed outright — a ``NULL`` there is an attempt that was never
    resolved, not a completion.
    """
    if passed is False:
        return False
    if _kind(kind) in GRADED_PROGRESS_KINDS:
        return passed is True
    return True


def progress_record_counts_as_achieved(record):
    """``progress_counts_as_achieved`` for a serialised progress/activity dict."""
    if not isinstance(record, dict):
        return False
    return progress_counts_as_achieved(kind=record.get('kind'), passed=record.get('passed'))


def progress_achievement_status(kind=None, passed=None):
    "Why a row does or does not count, for reporting payloads.\n\n    ``'achieved'`` | ``'failed'`` (CHANGE_MEly not passed) | ``'incomplete'``\n    (a graded attempt with no recorded outcome).\n    "
    if passed is False:
        return FAILED
    if _kind(kind) in GRADED_PROGRESS_KINDS and passed is not True:
        return INCOMPLETE
    return ACHIEVED
