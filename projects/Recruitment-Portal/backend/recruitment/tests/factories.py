from recruitment.models import Applicant, Application, Event, Question, Track


def event(slug="fair"):
    return Event.objects.create(title="Test fair", slug=slug)


def track(parent, code="software", order=10):
    return Track.objects.create(event=parent, name="Software", code=code, display_order=order)


def applicant(email="student@example.test"):
    return Applicant.objects.create(
        full_name="Test Student", email=email, mobile_number="01000000000",
        university="Test University", faculty_or_major="Engineering",
        education_status=Applicant.EducationStatus.STUDENT, city="Cairo",
    )


def application(parent, selected, person):
    return Application.objects.create(
        event=parent, track=selected, applicant=person,
        opportunity_type=Application.OpportunityType.INTERNSHIP,
        experience_level=Application.ExperienceLevel.NO_EXPERIENCE,
        preferred_work_arrangement=Application.WorkArrangement.FLEXIBLE,
        availability=Application.Availability.IMMEDIATELY,
    )


def question(selected, key="project", kind=Question.Type.LONG_TEXT, order=10):
    return Question.objects.create(track=selected, key=key, title=key, question_type=kind, display_order=order)
