from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.urls import reverse
from rest_framework import serializers
from .models import *
from .bank import unique_exam_questions
from .services.exhibit_storage import exhibit_proxy_url

User = get_user_model()

class LearnerProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="name", required=False)
    class Meta:
        model = LearnerProfile
        fields = ["id", "user", "user_type", "kbc_registry", "full_name", "name", "email", "job_title", "company_name", "industry", "role_description", "experience_level", "years_project_experience", "country", "is_kbc_learner", "programme", "cohort", "linkedin_url", "profile_completed", "apprenticeship_interest", "marketing_consent", "marketing_consent_at", "marketing_opted_out_at", "preferred_contact", "email_verified", "status", "future_lms_user_id", "future_lms_learner_id", "lms_linked_at", "last_seen_at"]
        read_only_fields = ["id", "user", "user_type", "kbc_registry", "email", "is_kbc_learner", "programme", "cohort", "marketing_consent_at", "marketing_opted_out_at", "email_verified", "status", "future_lms_user_id", "future_lms_learner_id", "lms_linked_at", "last_seen_at"]

class RegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    def validate_email(self, value): return normalize_email(value)
    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": 'CHANGE_ME'})
        validate_password(attrs["password"])
        return attrs

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    def validate_email(self, value): return normalize_email(value)
    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs["email"]).first()
        if not user:
            raise serializers.ValidationError({"email": "Invalid email or password."})
        authenticated = authenticate(username=user.username, password=attrs["password"])
        if not authenticated:
            raise serializers.ValidationError({"email": "Invalid email or password."})
        attrs["user"] = authenticated
        return attrs

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    def validate_email(self, value): return normalize_email(value)

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": 'CHANGE_ME'})
        validate_password(attrs["password"])
        return attrs

class KBCRegistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = KBCPmpLearnerRegistry
        fields = ["id", "source_learner_id", "full_name", "email", "programme", "cohort", "status", "is_active", "last_synced_at", "created_at"]
        read_only_fields = ["created_at"]

class DomainSerializer(serializers.ModelSerializer):
    class Meta: model = PMPDomain; fields = ["id", "name", "description"]

class TopicSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source="domain.name", read_only=True)
    available_questions = serializers.SerializerMethodField()
    class Meta: model = PMPTopic; fields = ["id", "domain", "domain_name", "name", "description", "available_questions"]
    def get_available_questions(self, obj): return len(unique_exam_questions(PMPQuestion.objects.filter(topic=obj)))
class PublicOptionSerializer(serializers.ModelSerializer):
    class Meta: model = PMPQuestionOption; fields = ["id", "option_label", "option_text"]

class PublicExhibitSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="exhibit_type", read_only=True)
    url = serializers.SerializerMethodField()
    class Meta:
        model = PMPExhibit
        fields = ["id", "title", "type", "url", "content", "caption", "source_exam", "source_question_number", "source_label"]
    def get_url(self, obj):
        if obj.external_url:
            return obj.external_url
        if obj.storage_backend in ("local", "azure") and obj.storage_path:
            request = self.context.get("request")
            path = reverse("pmp-exhibit-asset", kwargs={"exhibit_id": obj.id})
            return request.build_absolute_uri(path) if request else path
        return None

class PublicQuestionSerializer(serializers.ModelSerializer):
    options = PublicOptionSerializer(many=True, read_only=True)
    domain = serializers.SerializerMethodField()
    performance_domain = serializers.CharField(read_only=True)
    topic = serializers.SerializerMethodField()
    eco = serializers.SerializerMethodField()
    exhibit_url = serializers.SerializerMethodField()
    exhibits = serializers.SerializerMethodField()
    class Meta:
        model = PMPQuestion
        fields = ["id", "question_id", "question_text", "case_group_id", "case_text", "domain", "performance_domain", "eco", "topic", "task", "eco_task", "methodology", "question_type", "difficulty", "exhibit_url", "exhibit_alt_text", "exhibits", "options"]
    def get_domain(self, obj): return obj.performance_domain or (obj.domain.name if obj.domain_id else "Unmapped")
    def get_topic(self, obj): return obj.topic.name if obj.topic_id else None
    def get_eco(self, obj): return {"domain": obj.eco_domain or "", "task": obj.eco_task or obj.task}
    def get_exhibit_url(self, obj): return exhibit_proxy_url(obj.exhibit_blob_name) if obj.exhibit_blob_name else None
    def get_exhibits(self, obj):
        rows = list(obj.exhibits.all()) if hasattr(obj, "_prefetched_objects_cache") and "exhibits" in obj._prefetched_objects_cache else list(obj.exhibits.all())
        data = PublicExhibitSerializer(rows, many=True, context=self.context).data
        if not data and obj.exhibit_blob_name:
            data = [{"id": None, "title": obj.exhibit_alt_text or "Question exhibit", "type": "image", "url": exhibit_proxy_url(obj.exhibit_blob_name), "content": None, "caption": obj.exhibit_alt_text or "", "source_exam": "", "source_question_number": None, "source_label": ""}]
        return data

class AttemptCreateSerializer(serializers.Serializer):
    exam_mode = serializers.ChoiceField(choices=PMPExamAttempt.EXAM_MODES, default="domain")
    selected_domain_id = serializers.PrimaryKeyRelatedField(source="selected_domain", queryset=PMPDomain.objects.filter(name__in=PERFORMANCE_DOMAINS), required=False, allow_null=True)
    selected_topic_id = serializers.PrimaryKeyRelatedField(source="selected_topic", queryset=PMPTopic.objects.select_related("domain").filter(domain__name__in=PERFORMANCE_DOMAINS), required=False, allow_null=True)
    selected_methodology = serializers.ChoiceField(choices=PMPQuestion.METHODOLOGIES, required=False, allow_blank=True)
    selected_difficulty = serializers.ChoiceField(choices=PMPQuestion.DIFFICULTIES, required=False, allow_blank=True)
    question_count = serializers.ChoiceField(choices=[10, 20, 25, 40, 60, 100, 120, 180], required=False)
    def validate(self, attrs):
        mode = attrs.get("exam_mode", "domain")
        if mode == "domain" and not attrs.get("selected_domain"):
            raise serializers.ValidationError({"selected_domain_id": "Required for domain practice."})
        if mode == "topic" and not attrs.get("selected_topic"):
            raise serializers.ValidationError({"selected_topic_id": "Required for topic practice."})
        if mode == "methodology" and not attrs.get("selected_methodology"):
            raise serializers.ValidationError({"selected_methodology": "Required for methodology drills."})
        if mode == "difficulty" and not attrs.get("selected_difficulty"):
            raise serializers.ValidationError({"selected_difficulty": "Required for difficulty drills."})
        if mode == "domain": attrs["question_count"] = attrs.get("question_count") or 40
        elif mode == "exam_simulator": attrs["question_count"] = 180
        elif mode == "full_practice": attrs["question_count"] = attrs.get("question_count") or 180
        elif mode.startswith("practice_"): attrs["question_count"] = attrs.get("question_count") or 180
        else: attrs["question_count"] = attrs.get("question_count") or 10
        return attrs

class AnswerSaveSerializer(serializers.Serializer):
    selected_option_id = serializers.IntegerField(required=False)
    selected_option_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    current_question_index = serializers.IntegerField(min_value=0, required=False)
    is_flagged = serializers.BooleanField(required=False)
    def validate(self, attrs):
        if "selected_option_id" not in attrs and "selected_option_ids" not in attrs and "is_flagged" not in attrs:
            raise serializers.ValidationError("Provide selected_option_id, selected_option_ids, or is_flagged.")
        return attrs

class AdminOptionSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="option_label")
    text = serializers.CharField(source="option_text")
    class Meta: model = PMPQuestionOption; fields = ["id", "label", "text", "is_correct"]

class AdminQuestionSerializer(serializers.ModelSerializer):
    options = AdminOptionSerializer(many=True, required=False)
    domain = serializers.SlugRelatedField(slug_field="name", queryset=PMPDomain.objects.all(), required=False)
    topic = serializers.SlugRelatedField(slug_field="name", queryset=PMPTopic.objects.all(), allow_null=True, required=False)
    performance_domain = serializers.ChoiceField(choices=PERFORMANCE_DOMAIN_CHOICES, required=True)
    class Meta:
        model = PMPQuestion
        fields = ["id", "question_id", "performance_domain", "eco_domain", "eco_task", "question_type", "question_text", "case_group_id", "case_text", "domain", "topic", "task", "methodology", "difficulty", "correct_answer_explanation", "wrong_answer_explanation", "pmp_reference", "chapter_reference", "source_file", "source_sheet", "source_year", "source_item_id", "exhibit_blob_name", "exhibit_alt_text", "is_synthetic", "duplicate_of", "import_status", "is_active", "options", "created_at"]
        read_only_fields = ["created_at", "duplicate_of", "import_status"]
    def validate(self, attrs):
        options = attrs.get("options")
        if self.instance and options is None:
            options = [{"is_correct": option.is_correct} for option in self.instance.options.all()]
        if options is not None:
            if len(options) < 2: raise serializers.ValidationError({"options": "A question needs at least two options."})
            correct_count = sum(bool(x.get("is_correct")) for x in options)
            qtype = attrs.get("question_type") or (self.instance.question_type if self.instance else "Single Response")
            if qtype == "Multiple Response":
                if correct_count < 1: raise serializers.ValidationError({"options": "A multiple-response question needs at least one correct option."})
            elif correct_count != 1:
                raise serializers.ValidationError({"options": "Exactly one option must be correct unless the question type is Multiple Response."})
        return attrs
    def _domain_for_question(self, validated):
        if validated.get("domain"): return validated["domain"]
        domain, _ = PMPDomain.objects.get_or_create(name=validated["performance_domain"])
        return domain
    def create(self, validated):
        options = validated.pop("options", None)
        validated["domain"] = self._domain_for_question(validated)
        validated.setdefault("eco_task", validated.get("task", ""))
        question = PMPQuestion.objects.create(**validated)
        if options: PMPQuestionOption.objects.bulk_create([PMPQuestionOption(question=question, **x) for x in options])
        return question
    def update(self, instance, validated):
        options = validated.pop("options", None)
        if "performance_domain" in validated and "domain" not in validated:
            validated["domain"] = self._domain_for_question(validated)
        for key, value in validated.items(): setattr(instance, key, value)
        instance.full_clean(); instance.save()
        if options is not None:
            instance.options.all().delete()
            PMPQuestionOption.objects.bulk_create([PMPQuestionOption(question=instance, **x) for x in options])
        return instance

class AttemptSummarySerializer(serializers.ModelSerializer):
    selected_domain_name = serializers.CharField(source="selected_domain.name", read_only=True)
    selected_topic_name = serializers.CharField(source="selected_topic.name", read_only=True)
    class Meta:
        model = PMPExamAttempt
        fields = ["id", "exam_mode", "selected_domain", "selected_domain_name", "selected_topic", "selected_topic_name", "selected_methodology", "selected_difficulty", "question_count", "duration_minutes", "started_at", "submitted_at", "last_activity_at", "current_question_index", "status", "score_percentage", "correct_count", "incorrect_count"]
