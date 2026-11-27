from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
from .bank import PERFORMANCE_DOMAINS, bank_readiness_stats, canonical_signature, official_eco_domain, official_eco_quotas, unique_exam_questions
from .models import *
from .services.exhibit_storage import EXPECTED_EXHIBIT_BLOBS
from .views import clear_question_selection_caches, practice_mock_questions

User = get_user_model()

class AssessmentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=False)
        self.staff = User.objects.create_user("staff", email="staff@example.com", password='CHANGE_ME', is_staff=True)
        self.domains = {name: PMPDomain.objects.get_or_create(name=name)[0] for name in PERFORMANCE_DOMAINS}
        self.topics = {name: PMPTopic.objects.get_or_create(domain=domain, name=f"{name} Topic")[0] for name, domain in self.domains.items()}
        for domain_name in PERFORMANCE_DOMAINS:
            for i in range(45): self.create_question(domain_name, i)
        self.user = User.objects.create_user("alex@example.com", email="alex@example.com", password='CHANGE_ME')
        self.profile = LearnerProfile.objects.create(user=self.user, name="Alex", email="alex@example.com", user_type="EXTERNAL", email_verified=True)
    def create_question(self, domain_name="Risk", number=0, text=None, qtype="Single Response", active=True, duplicate_of=None, synthetic=False, source_file="", eco_domain="II"):
        domain = self.domains.get(domain_name) or PMPDomain.objects.create(name=domain_name)
        topic = self.topics.get(domain_name) or PMPTopic.objects.create(domain=domain, name=f"{domain_name} Topic")
        q = PMPQuestion.objects.create(question_id=f"{domain_name[:3]}-{number}", question_text=text or f"{domain_name} Question {number}", domain=domain, topic=topic,
            performance_domain=domain_name if domain_name in PERFORMANCE_DOMAINS else "", eco_domain=eco_domain, eco_task=f"{domain_name}.{number}", methodology="Hybrid", question_type=qtype,
            correct_answer_explanation="Because it is correct.", is_active=active, duplicate_of=duplicate_of, is_synthetic=synthetic, source_file=source_file)
        PMPQuestionOption.objects.create(question=q, option_label="A", option_text="Correct", is_correct=True)
        PMPQuestionOption.objects.create(question=q, option_label="B", option_text="Wrong")
        if qtype == "Multiple Response": PMPQuestionOption.objects.create(question=q, option_label="C", option_text="Also correct", is_correct=True)
        return q
    def auth(self, user=None): self.client.force_authenticate(user=user or self.user)
    def create_attempt(self, domain="Risk"):
        self.auth(); return self.client.post("/api/pmp/attempts/", {"exam_mode":"domain", "selected_domain_id": self.domains[domain].id}, format="json")
    def test_registration_detects_kbc_registry_and_normalizes_email(self):
        KBCPmpLearnerRegistry.objects.create(full_name="Sarah Learner", email=' contact+54a5c130b28d@example.com ', programme="Project Controls Professional L6", cohort="C1")
        response = self.client.post("/api/pmp/auth/register/", {"email":'contact+54a5c130b28d@example.com', "password":'CHANGE_ME', "confirm_password":'CHANGE_ME'}, format="json")
        self.assertEqual(response.status_code, 201)
        profile = LearnerProfile.objects.get(email='contact+54a5c130b28d@example.com')
        self.assertEqual(profile.user_type, "KBC_LEARNER")
        self.assertEqual(profile.programme, "Project Controls Professional L6")
    def test_external_registration_and_duplicate_prevention(self):
        response = self.client.post("/api/pmp/auth/register/", {"full_name":"New User", "email":"New@Example.COM", "password":'CHANGE_ME', "confirm_password":'CHANGE_ME'}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(LearnerProfile.objects.get(email="new@example.com").user_type, "EXTERNAL")
        duplicate = self.client.post("/api/pmp/auth/register/", {"full_name":"New User", "email":"new@example.com", "password":'CHANGE_ME', "confirm_password":'CHANGE_ME'}, format="json")
        self.assertEqual(duplicate.status_code, 400)
    def test_login_logout_and_me(self):
        response = self.client.post("/api/pmp/auth/login/", {"email":"alex@example.com", "password":'CHANGE_ME'}, format="json")
        self.assertEqual(response.status_code, 200)
        self.auth(); self.assertEqual(self.client.get("/api/pmp/me/").status_code, 200)
        self.assertEqual(self.client.post("/api/pmp/auth/logout/").status_code, 200)
    def test_email_verification_and_password_reset(self):
        token_row = PMPAuthToken.objects.create(user=self.user, purpose="email_verification", token_hash=__import__("hashlib").sha256(b"verify").hexdigest(), expires_at=__import__("django").utils.timezone.now()+__import__("datetime").timedelta(hours=1))
        response = self.client.post("/api/pmp/auth/verify-email/", {"token":'CHANGE_ME'}, format="json")
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db(); self.assertTrue(self.profile.email_verified)
        self.assertEqual(self.client.post("/api/pmp/auth/password-reset/", {"email":"alex@example.com"}, format="json").status_code, 200)
    def test_security_requires_auth_and_ownership(self):
        self.assertIn(self.client.get("/api/pmp/dashboard/").status_code, (401, 403))
        attempt = self.create_attempt().data
        other = User.objects.create_user("other@example.com", email="other@example.com", password='CHANGE_ME')
        LearnerProfile.objects.create(user=other, name="Other", email="other@example.com")
        self.auth(other)
        self.assertEqual(self.client.get(f"/api/pmp/attempts/{attempt['id']}/questions/").status_code, 404)
    def test_correct_answers_hidden_during_attempt(self):
        attempt = self.create_attempt().data
        response = self.client.get(f"/api/pmp/attempts/{attempt['id']}/questions/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("is_correct", str(response.data))
        self.assertNotIn("correct_answer", str(response.data))
    def test_only_supported_performance_domains_are_accepted(self):
        q = self.create_question("Risk", 999); q.performance_domain = "People"
        with self.assertRaises(ValidationError): q.full_clean()
    def test_question_requires_performance_domain_before_exam_ready(self):
        unmapped = self.create_question("Risk", 1000); unmapped.performance_domain = ""; unmapped.save(update_fields=["performance_domain"])
        self.assertNotIn(unmapped.id, [q.id for q in unique_exam_questions()])
    def test_question_bank_retains_more_than_40_questions_and_readiness_uses_threshold(self):
        stats = bank_readiness_stats(); risk = next(x for x in stats["domains"] if x["name"] == "Risk")
        self.assertGreaterEqual(risk["count"], 45)
        self.assertTrue(risk["ready"])
        self.assertEqual(risk["required"], 40)
    def test_bank_not_ready_when_one_domain_has_fewer_than_40(self):
        PMPQuestion.objects.filter(id__in=list(PMPQuestion.objects.filter(performance_domain="Finance").values_list("id", flat=True)[:10])).delete()
        finance = next(x for x in bank_readiness_stats()["domains"] if x["name"] == "Finance")
        self.assertFalse(finance["ready"]); self.assertEqual(finance["missing"], 5)
    def test_domain_exam_creates_exactly_40_unique_questions_from_selected_domain(self):
        response = self.create_attempt("Risk")
        self.assertEqual(response.status_code, 201)
        links = PMPExamAttemptQuestion.objects.filter(attempt_id=response.data["id"])
        self.assertEqual(links.count(), 40)
        self.assertEqual(links.values("question_id").distinct().count(), 40)
        self.assertTrue(all(x == "Risk" for x in links.values_list("question__performance_domain", flat=True)))
    def test_domain_exam_includes_visual_questions_when_available(self):
        visual = self.create_question("Scope", 6102)
        visual.exhibit_blob_name = "scope/sc-027.png"
        visual.exhibit_alt_text = "Scope chart exhibit"
        visual.save(update_fields=["exhibit_blob_name", "exhibit_alt_text"])
        response = self.create_attempt("Scope")
        self.assertEqual(response.status_code, 201)
        links = PMPExamAttemptQuestion.objects.filter(attempt_id=response.data["id"])
        self.assertTrue(links.filter(question__exhibit_blob_name="scope/sc-027.png").exists())
    def test_full_simulator_creates_180_unique_mixed_domain_questions(self):
        for i in range(3): self.create_question("Governance", 9000+i)
        self.auth()
        response = self.client.post("/api/pmp/attempts/", {"exam_mode":"exam_simulator"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["question_count"], 180)
        self.assertEqual(response.data["duration_minutes"], 240)
        links = PMPExamAttemptQuestion.objects.filter(attempt_id=response.data["id"])
        self.assertEqual(links.count(), 180)
        self.assertEqual(links.values("question_id").distinct().count(), 180)
        counts = dict(links.values_list("question__performance_domain").annotate(total=Count("id")))
        self.assertEqual(set(counts), set(PERFORMANCE_DOMAINS))
        self.assertEqual(sum(counts.values()), 180)
        self.assertTrue(all(value > 0 for value in counts.values()))

    def test_imported_mock_uses_sheet_questions_and_legacy_to_match_eco_quota(self):
        for i in range(120):
            domain = "Stakeholders" if i < 40 else "Scope" if i < 90 else "Governance"
            eco = "People" if i < 40 else "Process" if i < 90 else "Business Environment"
            self.create_question(domain, 7000+i, source_file="exam02.xlsx", eco_domain=eco)
        for i in range(10):
            self.create_question("Scope", 7200+i, text=f"Prior mock duplicate {i}", source_file="exam01.xlsx", eco_domain="Process")
        for i in range(80):
            self.create_question("Stakeholders", 7300+i, source_file="legacy.xlsx", eco_domain="People")
            self.create_question("Scope", 7400+i, source_file="legacy.xlsx", eco_domain="Process")
            self.create_question("Governance", 7500+i, source_file="legacy.xlsx", eco_domain="Business Environment")
        clear_question_selection_caches()

        questions, error, imported_count = practice_mock_questions("exam02.xlsx", "practice_2", 180)

        self.assertEqual(error, "")
        self.assertEqual(imported_count, 120)
        self.assertEqual(len(questions), 180)
        self.assertEqual(len({canonical_signature(q) for q in questions}), 180)
        self.assertEqual(sum(1 for q in questions if q.source_file == "exam02.xlsx"), 120)
        self.assertEqual(sum(1 for q in questions if not str(q.source_file or "").lower().startswith("exam")), 60)
        self.assertEqual(
            {domain: sum(1 for q in questions if official_eco_domain(q) == domain) for domain in official_eco_quotas(180)},
            official_eco_quotas(180),
        )

    def test_quick_practice_creates_requested_count_from_all_or_domain(self):
        self.auth()
        response = self.client.post("/api/pmp/attempts/", {"exam_mode":"quick", "question_count":20}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["question_count"], 20)
        self.assertEqual(response.data["duration_minutes"], 30)
        self.assertEqual(PMPExamAttemptQuestion.objects.filter(attempt_id=response.data["id"]).count(), 20)
        PMPExamAttempt.objects.filter(id=response.data["id"]).update(status="submitted")
        domain_response = self.client.post("/api/pmp/attempts/", {"exam_mode":"quick", "question_count":10, "selected_domain_id":self.domains["Scope"].id}, format="json")
        self.assertEqual(domain_response.status_code, 201)
        self.assertTrue(all(x == "Scope" for x in PMPExamAttemptQuestion.objects.filter(attempt_id=domain_response.data["id"]).values_list("question__performance_domain", flat=True)))

    def test_active_attempt_blocks_starting_another_attempt(self):
        first = self.create_attempt("Risk")
        self.assertEqual(first.status_code, 201)
        second = self.client.post("/api/pmp/attempts/", {"exam_mode":"quick", "question_count":10}, format="json")
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["attempt"]["id"], first.data["id"])
    def test_domain_with_fewer_than_40_uses_available_question_count(self):
        PMPQuestion.objects.filter(id__in=list(PMPQuestion.objects.filter(performance_domain="Governance").values_list("id", flat=True)[:8])).delete()
        response = self.create_attempt("Governance")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["question_count"], 37)
        self.assertEqual(PMPExamAttemptQuestion.objects.filter(attempt_id=response.data["id"]).count(), 37)
    def test_inactive_synthetic_and_duplicate_questions_excluded(self):
        inactive = self.create_question("Risk", 2001, active=False)
        synthetic = self.create_question("Risk", 2002, synthetic=True)
        duplicate = self.create_question("Risk", 2003, text="Risk Question 2")
        ids = {q.id for q in unique_exam_questions()}
        self.assertNotIn(inactive.id, ids); self.assertNotIn(synthetic.id, ids); self.assertNotIn(duplicate.id, ids)
    def test_refresh_returns_same_40_and_answers_persist(self):
        attempt = self.create_attempt("Risk").data; first = self.client.get(f"/api/pmp/attempts/{attempt['id']}/questions/").data
        q = first["questions"][0]; option = q["options"][0]
        self.assertEqual(self.client.put(f"/api/pmp/attempts/{attempt['id']}/answers/{q['id']}/", {"selected_option_id": option["id"], "current_question_index": 3}, format="json").status_code, 200)
        second = self.client.get(f"/api/pmp/attempts/{attempt['id']}/questions/").data
        self.assertEqual([x["id"] for x in first["questions"]], [x["id"] for x in second["questions"]])
        self.assertEqual(second["answers"][q["id"]], [option["id"]])
        self.assertEqual(second["current_question_index"], 3)
    def test_submit_locks_attempt_and_scores_multiple_response(self):
        for q in PMPQuestion.objects.filter(performance_domain="Risk")[:5]: q.delete()
        multi = self.create_question("Risk", 3000, qtype="Multiple Response")
        attempt = self.create_attempt("Risk").data
        questions = self.client.get(f"/api/pmp/attempts/{attempt['id']}/questions/").data["questions"]
        for q in questions:
            ids = [o["id"] for o in q["options"] if o["option_label"] in (["A","C"] if q["question_type"] == "Multiple Response" else ["A"])]
            self.client.put(f"/api/pmp/attempts/{attempt['id']}/answers/{q['id']}/", {"selected_option_ids": ids}, format="json")
        result = self.client.post(f"/api/pmp/attempts/{attempt['id']}/submit/", {}, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["score_percentage"], 100)
        self.assertEqual(self.client.put(f"/api/pmp/attempts/{attempt['id']}/answers/{questions[0]['id']}/", {"selected_option_id": questions[0]["options"][1]["id"]}, format="json").status_code, 409)
    def test_abandon_discards_in_progress_attempt_without_result(self):
        attempt = self.create_attempt("Risk").data
        question = self.client.get(f"/api/pmp/attempts/{attempt['id']}/questions/").data["questions"][0]
        option = question["options"][0]
        self.assertEqual(self.client.put(f"/api/pmp/attempts/{attempt['id']}/answers/{question['id']}/", {"selected_option_id": option["id"]}, format="json").status_code, 200)
        response = self.client.post(f"/api/pmp/attempts/{attempt['id']}/abandon/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PMPExamAttempt.objects.filter(id=attempt["id"]).exists())
        self.assertFalse(PMPExamAnswer.objects.filter(attempt_id=attempt["id"]).exists())
        self.assertEqual(self.client.get(f"/api/pmp/attempts/{attempt['id']}/result/").status_code, 404)
    def test_delete_attempt_removes_attempt_history_row(self):
        attempt = self.create_attempt("Risk").data
        response = self.client.delete(f"/api/pmp/attempts/{attempt['id']}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(PMPExamAttempt.objects.filter(id=attempt["id"]).exists())
        self.assertEqual(self.client.get(f"/api/pmp/attempts/{attempt['id']}/").status_code, 404)
    def test_case_study_and_graphic_questions_remain_exam_ready(self):
        case = self.create_question("Scope", 4001, qtype="Case Study"); graphic = self.create_question("Schedule", 4002, qtype="Graphic")
        ids = [q.id for q in unique_exam_questions()]
        self.assertIn(case.id, ids); self.assertIn(graphic.id, ids)
    def test_normal_question_returns_null_exhibit_url(self):
        q = self.create_question("Risk", 6100)
        attempt = PMPExamAttempt.objects.create(learner_profile=self.profile, exam_mode="domain", selected_domain=self.domains["Risk"], question_count=1, duration_minutes=60, status="in_progress")
        PMPExamAttemptQuestion.objects.create(attempt=attempt, question=q, order_number=1)
        self.auth(); response = self.client.get(f"/api/pmp/attempts/{attempt.id}/questions/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["questions"][0]["exhibit_url"])

    @override_settings(AZURE_PMP_EXHIBIT_READ_SAS="sv=secret&sig=never-return-this")
    def test_visual_question_returns_proxy_exhibit_url_without_credentials(self):
        q = self.create_question("Schedule", 6101)
        q.exhibit_blob_name = "schedule/ag-001.png"
        q.exhibit_alt_text = "Agile chart exhibit"
        q.save(update_fields=["exhibit_blob_name", "exhibit_alt_text"])
        attempt = PMPExamAttempt.objects.create(learner_profile=self.profile, exam_mode="domain", selected_domain=self.domains["Schedule"], question_count=1, duration_minutes=60, status="in_progress")
        PMPExamAttemptQuestion.objects.create(attempt=attempt, question=q, order_number=1)
        self.auth(); response = self.client.get(f"/api/pmp/attempts/{attempt.id}/questions/")
        self.assertEqual(response.status_code, 200)
        payload = response.data["questions"][0]
        self.assertIn("/api/pmp/exhibits/schedule/ag-001.png/", payload["exhibit_url"])
        self.assertEqual(payload["exhibit_alt_text"], "Agile chart exhibit")
        self.assertNotIn("sig=", str(response.data))
        self.assertNotIn("never-return-this", str(response.data))
        self.assertNotIn("is_correct", str(response.data))

    def test_upload_exhibit_command_validates_10_unique_assets_and_is_repeatable(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for blob_name in EXPECTED_EXHIBIT_BLOBS:
                target = root / blob_name
                target.parent.mkdir(parents=True, exist_ok=True)
                image = Image.new("RGB", (3, 3), "white")
                image.putpixel((0, 0), (0, 0, 0))
                image.save(target)
            first = StringIO(); second = StringIO()
            call_command("upload_pmp_exhibits", source_dir=str(root), dry_run=True, stdout=first)
            call_command("upload_pmp_exhibits", source_dir=str(root), dry_run=True, stdout=second)
            self.assertIn("Validated 10 unique", first.getvalue())
            self.assertIn("Validated 10 unique", second.getvalue())
            self.assertEqual(len(EXPECTED_EXHIBIT_BLOBS), 10)
            self.assertNotIn("sch-004.png", " ".join(EXPECTED_EXHIBIT_BLOBS))
    def test_admin_filters_and_external_cannot_access_admin(self):
        self.auth(); self.assertEqual(self.client.get("/api/pmp/admin/questions/").status_code, 403)
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/pmp/admin/questions/?performance_domain=Governance&methodology=Hybrid&question_type=Single%20Response&active=true")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data)
        self.assertTrue(all(q["performance_domain"] == "Governance" for q in response.data))
    def test_historical_inactive_question_still_renders(self):
        old = self.create_question("Risk", 5001, active=False)
        attempt = PMPExamAttempt.objects.create(learner_profile=self.profile, exam_mode="domain", selected_domain=self.domains["Risk"], question_count=1, duration_minutes=60, status="in_progress")
        PMPExamAttemptQuestion.objects.create(attempt=attempt, question=old, order_number=1)
        self.auth(); response = self.client.get(f"/api/pmp/attempts/{attempt.id}/questions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["questions"][0]["id"], old.id)
