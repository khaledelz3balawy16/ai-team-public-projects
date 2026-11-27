from django.contrib.auth.models import User
from django.test import TestCase

from .admin import EmailRequiredUserChangeForm, EmailRequiredUserCreationForm


class EmailRequiredUserCreationFormTests(TestCase):
    def test_email_is_required(self):
        form = EmailRequiredUserCreationForm(
            data={
                "username": "Youmna",
                "email": "",
                "password1": 'CHANGE_ME',
                "password2": 'CHANGE_ME',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_existing_user_can_keep_their_email(self):
        user = User.objects.create_user(
            username="existing-user",
            email='contact+ebe8ead896ab@example.com',
            password='CHANGE_ME',
        )
        form = EmailRequiredUserChangeForm(
            instance=user,
            data={
                "username": user.username,
                "email": user.email,
                "is_active": True,
            },
        )

        self.assertNotIn("email", form.errors)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            username="existing-user",
            email='contact+ebe8ead896ab@example.com',
            password='CHANGE_ME',
        )
        form = EmailRequiredUserCreationForm(
            data={
                "username": "another-user",
                "email": 'contact+ebe8ead896ab@example.com',
                "password1": 'CHANGE_ME',
                "password2": 'CHANGE_ME',
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

# Create your tests here.
