from django.contrib.auth import authenticate

# Test authentication for a coach account
username = 'Omar Elshafey'
password = 'CHANGE_ME'

user = authenticate(username=username, password=password)

if user:
    print(f'✓ Login successful!')
    print(f'  Username: {user.username}')
    print(f'  Role: {user.profile.role}')
    print(f'  Coach ID: {user.profile.coach_id}')
    print(f'\n✓ This coach will only see data for coach_id: {user.profile.coach_id}')
else:
    print('✗ Login failed')
