# Pathway

Flutter client for the Pathway workspace. See [Architecture](docs/architecture.md)
for the feature map, state/data flow, refactor inventory, and development checks.

## Run

```sh
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8080
```

The default URL targets a backend on the Android emulator's host machine.
Provide the appropriate backend URL for other devices. Release builds require
an HTTPS API URL under the existing configuration guard.

## Validate

```sh
flutter analyze
flutter test
flutter build apk --debug
```

Production code is under `lib/`; native runners are under the platform folders.
The tests use fake API responses and do not require a running backend.
