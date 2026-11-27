from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile


class Command(BaseCommand):
    help = 'Create individual coach accounts with restricted access'

    def handle(self, *args, **options):
        # List of coach names with emails - each can log in with name or email
        coaches = [
            {"name": "Omar Elshafey", "email": 'contact+d9c4db65fc4f@example.com'},
            {"name": "Radwa Samir", "email": 'contact+22b187d97ef2@example.com'},
            {"name": "Omar Badr", "email": 'contact+8982bc9dfbfe@example.com'},
            {"name": "Ahmed Maher", "email": 'contact+be9a41e30dc0@example.com'},
            {"name": "Femi Falodun", "email": 'contact+167263910ecc@example.com'},
            {"name": "Nathan Shields", "email": 'contact+459ef75604cd@example.com'},
            {"name": "Hannen Mostafa", "email": 'contact+9359e11980b7@example.com'},
            {"name": "Nouran Abdalla", "email": 'contact+0c695a926e1c@example.com'},
            {"name": "Afaan Khan", "email": 'contact+37c9538dcddd@example.com'},
            {"name": "Adeyemi Adeshina", "email": 'contact+72398d95e84c@example.com'},
            {"name": "Marwa Mahmoud", "email": 'contact+7ab1e17fe08f@example.com'},
            {"name": "Mahinor Hesham", "email": 'contact+5ef96d9a2817@example.com'},
            {"name": "Omar Ham", "email": 'contact+9a587b4d99d6@example.com'},
            {"name": "Aryan Harikumar", "email": 'contact+2537a231e45b@example.com'},
            {"name": "Elaf Mansour", "email": 'contact+364fb9219f55@example.com'},
            {"name": "Olivia Evans", "email": 'contact+3bc97a343f1a@example.com'},
            {"name": "Patryk Zajac", "email": 'contact+8dc53252c136@example.com'},
        ]

        password = 'CHANGE_ME'
        created_count = 0
        updated_count = 0

        for idx, coach_data in enumerate(coaches, start=1):
            # Use coach_id as the sequential number
            coach_id = str(idx)
            coach_name = coach_data["name"]
            coach_email = coach_data["email"]

            # Check if user already exists
            user, created = User.objects.get_or_create(
                username=coach_name,
                defaults={
                    'first_name': coach_name.split()[0],
                    'last_name': ' '.join(coach_name.split()[1:]) if len(coach_name.split()) > 1 else '',
                    'email': coach_email,
                }
            )

            # Set password and email (will update if user already exists)
            user.set_password(password)
            user.email = coach_email
            user.save()

            # Create or update profile
            profile, profile_created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'coach',
                    'coach_id': coach_id,
                }
            )

            # Update profile if it already exists
            if not profile_created:
                profile.role = 'coach'
                profile.coach_id = coach_id
                profile.save()
                updated_count += 1
            else:
                created_count += 1

            status = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ {status.capitalize()} coach account: {coach_name} | Email: {coach_email} (coach_id: {coach_id})'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Done! Created {created_count} new accounts, updated {updated_count} existing accounts.'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Password for all coach accounts: {password}'
            )
        )
