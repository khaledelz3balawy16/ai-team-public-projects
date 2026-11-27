# Pathway Flutter architecture

`lib/main.dart` is the entry point. `app.dart` owns the app theme and session gate.
There is one Flutter package and one Dart source tree: `lib/`. The `ios/` folder
contains the native iOS runner; it does not contain a second Dart app.

## Dependency flow

Screens compose widgets and forward user actions. Controllers own state and
coordinate requests. Repositories expose workspace data operations. Services
perform HTTP, credential storage, file picking, temporary-file handling, and
external file opening.

State management remains Flutter `State` and `setState`. Controllers are plain
Dart objects with callbacks; no state-management dependency was added. Screen
instances provide mounted checks so late async results do not update disposed UI.

`WorkspaceFormPresenter` opens modal sheets and builds UI field specifications.
Feature extensions define each action's fields and payload transformations.
The controller submits requests, reloads bootstrap data, and refreshes the
selected lead through the same sequence as before. Form validation errors and
server errors still stay inside the sheet.

## Source map

```text
lib/
  main.dart
  app.dart
  config/app_config.dart
  core/
    constants/app_colors.dart
    errors/api_exception.dart
    routes/workspace_routes.dart
    theme/app_theme.dart
    utils/data_helpers.dart
  features/
    authentication/{controllers,screens,services}/
    home/{controllers,models,repositories,screens,widgets}/
    leads/{models,screens,widgets}/
    planner/{models,screens,widgets}/
    inbox/{screens,widgets}/
    applications/{models,screens,widgets}/
    events/screens/
    attribution/screens/
    profile/{screens,widgets}/
    audit/screens/
  shared/
    components/form_field_spec.dart
    widgets/
  services/
    api/pathway_api.dart
    storage/{session_storage,evidence_file_service}.dart
```

Empty `models`, `extensions`, and `network` directories are not created merely
as placeholders. Add them when a concrete shared model, extension, or transport
abstraction is needed. Current transport logic fits in `PathwayApi`.

The workspace bootstrap remains a single server aggregate. Its shared controller
therefore stays in `home`; splitting it into independent feature stores would
change refresh and busy-state semantics. Feature pages accept that controller
explicitly. Models retain unknown JSON fields and offer `fromJson`/`toJson`.
`FormFieldSpec` is UI configuration and belongs in shared components, not domain
models. `workspace_models.dart` is a compatibility export of the separated models.

## Refactor inventory

| Original location | Responsibility after refactoring |
| --- | --- |
| `main.dart` | Minimal entry point; app composition in `app.dart` |
| `authentication/screens/login_screen.dart` | UI and text input; asynchronous state in `LoginController`, API access in `AuthenticationService` |
| `home/screens/workspace_screen.dart` (576 lines) | Workspace shell; active state/data flow in `WorkspaceController`, modal UI in `WorkspaceFormPresenter`, file integration in `EvidenceFileService` |
| `home/screens/workspace_views.dart` (475 lines) | Today, More, leads, lead detail, planner, inbox, applications, events, attribution, settings, and audit page widgets in their feature folders |
| `home/screens/workspace_actions.dart` (348 lines) | Lead, activity, email, application, and team form presenters in feature widget folders |
| Duplicated workspace helper methods | One shared workspace UI helper implementation; reusable lead cards in `leads/widgets/lead_card.dart` |
| Unused `WorkspaceController` implementation | Replaced with the actual running screen logic, preserving its error and refresh semantics |
| `home/models/workspace_models.dart` | Individual snapshot, lead, task, and application model files |
| `services/api/pathway_api.dart` | HTTP and session API; exception in `core/errors`, secure-store access in `services/storage` |
| `shared/widgets/action_form.dart` | Modal form widget; field metadata in `shared/components/form_field_spec.dart` |

Existing shared widgets include ActionForm, EmptyState, Notice, PersonAvatar,
SectionCard, and StatusBadge. Pure data helpers handle record conversion, names,
dates, and overdue checks. Theme, colors, and API configuration retain their values.

The pre-refactor code had unused duplicate controller/helper implementations,
large private `part` files, API and plugin calls in screens, and a generic
`Workspace` widget name. The shell is now named `WorkspaceScreen`. Feature page
names identify the page they render. Previously unused form actions are retained;
this refactor does not expose additional buttons or remove workflows.

## Preserved behavior

- Endpoint paths, HTTP methods, request payloads, timeout values, and credential keys.
- Section-based navigation, More fallback, detail/back transitions, and filters.
- Existing labels, styles, layout values, permission checks, and button availability.
- Latest-bootstrap-response handling and mounted guards.
- Session-expiry handling, mutation notifications, and post-save refresh order.
- Evidence file extensions, 5 MB limit, base64 payload, cache cleanup, and file opening.

Existing planner filter semantics and text rendering are intentionally retained.
Correcting a pre-existing product behavior should be a separate change.

## Continuing development

Add a page under its feature's `screens`, reusable UI under `widgets`, and data
operations in a service or the aggregate repository. Keep screen files focused on
composition. Register workspace sections in `core/routes/workspace_routes.dart`;
the existing bottom navigation remains in the workspace shell.

Run `flutter analyze`, `flutter test`, and `flutter build apk --debug` from the
project root. API configuration remains `--dart-define=API_BASE_URL=...`; the
default Android-emulator address is `http://10.0.2.2:8080`. Release builds retain
the existing HTTPS configuration guard.

The regression suite exercises stale responses, mounted checks, session expiry,
mutations, search, login, and navigation/form composition. It uses fake API data
and does not prove live backend, device file-picker, or iOS integration behavior.

Verification completed on 2026-09-21:

- `flutter analyze --no-pub`: no issues.
- `flutter test --no-pub`: all 12 tests passed.
- `flutter build apk --debug --no-pub`: succeeded.
- Built APK installed and launched with `flutter run --no-resident` on
  `emulator-5554` (Android 17); Flutter loaded and the command exited successfully.

The build installed missing Android SDK Platforms 34/35 and CMake 3.22.1. It
reported existing plugin/toolchain warnings about `file_picker`'s Kotlin Gradle
plugin and Java 8 compile targets; no dependencies or build settings were changed
to address those warnings in this architecture-only refactor.

Because this directory was not a Git checkout, the original source, tests, and
README were archived at `.refactor-backup/before.zip` before editing.
