# شرح تقسيمة مشروع Pathway

هذا الملف يشرح تنظيم المشروع الحالي وأين تضع كل نوع من التعديلات. التطبيق مكتوب بـ Flutter وDart، والكود الأساسي موجود في `lib/`.

## 1. فكرة التقسيم

المشروع مقسّم حسب الوظائف (Features)، مثل تسجيل الدخول والعملاء والطلبات. داخل كل وظيفة تُفصل الشاشات عن منطق التحكم والبيانات حسب الحاجة.

إدارة الحالة الحالية تعتمد على `State` و`setState`. الـ Controllers كائنات Dart عادية ترسل إشعارات عبر callbacks؛ المشروع لا يستخدم Bloc أو Provider لإدارة الحالة.

## 2. شجرة الملفات الأساسية

```text
lib/
├── main.dart
├── app.dart
├── config/
│   └── app_config.dart
├── core/
│   ├── constants/app_colors.dart
│   ├── errors/api_exception.dart
│   ├── routes/workspace_routes.dart
│   ├── theme/app_theme.dart
│   └── utils/data_helpers.dart
├── features/
│   ├── authentication/   # تسجيل الدخول
│   ├── home/             # إدارة مساحة العمل والشاشات الرئيسية
│   ├── leads/            # العملاء المحتملون وتفاصيلهم
│   ├── planner/          # المهام والأنشطة
│   ├── inbox/            # البريد
│   ├── applications/     # الطلبات ومستنداتها
│   ├── events/           # الفعاليات
│   ├── attribution/      # الإسناد ومصادر العملاء
│   ├── profile/          # الإعدادات ونماذج الفريق
│   └── audit/            # سجل التدقيق
├── shared/
│   ├── components/form_field_spec.dart
│   └── widgets/
└── services/
    ├── api/pathway_api.dart
    └── storage/
        ├── session_storage.dart
        └── evidence_file_service.dart
```

## 3. نقطة البداية والإعدادات

| الملف | دوره |
| --- | --- |
| `lib/main.dart` | نقطة تشغيل التطبيق؛ يستدعي `PathwayApp`. |
| `lib/app.dart` | ينشئ عميل API، ويحاول استعادة الجلسة، ويختار شاشة الدخول أو مساحة العمل، ويطبّق الثيم. |
| `lib/config/app_config.dart` | يقرأ عنوان الخادم من `API_BASE_URL` ويحدد صلاحية استخدامه في وضع Release وفق شرط HTTPS. |

العنوان الافتراضي هو `http://10.0.2.2:8080`، للوصول من محاكي Android إلى خادم يعمل على الجهاز المضيف. يمكن تغييره عند التشغيل:

```sh
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8080
```

## 4. الفرق بين المجلدات داخل كل Feature

| المجلد | ماذا يحتوي؟ |
| --- | --- |
| `screens/` | الشاشات وتجميع عناصر الواجهة واستقبال تفاعل المستخدم. |
| `widgets/` | عناصر الواجهة والنماذج الخاصة بالوظيفة. |
| `controllers/` | الحالة والبحث والفلاتر وتنسيق تنفيذ العمليات وتحديث الواجهة. |
| `models/` | تمثيل البيانات والتعامل مع JSON. |
| `repositories/` | عمليات الوصول إلى بيانات مساحة العمل من خلال خدمة API. |
| `services/` | خدمات خاصة بالوظيفة، مثل خدمة تسجيل الدخول. |

ليست كل وظيفة بحاجة إلى جميع هذه المجلدات. مثلًا `events` يحتوي حاليًا على شاشته، بينما `home` يحتوي على Controller وRepository مشتركين لمساحة العمل.

## 5. مساحة العمل وملف WorkspaceController

الملف `lib/features/home/controllers/workspace_controller.dart` مسؤول عن الحالة المشتركة لمساحة العمل، ومنها:

- `data`: البيانات القادمة من الخادم.
- `section`: القسم المعروض حاليًا، مثل `today` أو `leads`.
- `search` و`stage` و`taskFilter` و`emailFilter`: البحث والفلاتر.
- `detail`: تفاصيل العميل المفتوح.
- `busy` و`error`: حالة تنفيذ العملية والخطأ المعروض.
- `load()`: تحميل البيانات، مع استخدام `loadVersion` لمنع نتيجة تحميل أقدم من استبدال نتيجة أحدث ناجحة.
- `navigate()` و`openLead()`: تغيير القسم وفتح تفاصيل العميل.
- `mutate()`: إرسال تعديل ثم إعادة تحميل البيانات وإظهار رسالة.
- `handleError()`: التعامل مع الأخطاء، ومنها إنهاء الجلسة عند استجابة `401`.
- `uploadEvidence()` و`openEvidence()`: تنسيق رفع وفتح المستندات باستخدام خدمة الملفات.

الـ Controller لا يبني الواجهة بنفسه. `WorkspaceScreen` يمرّر له `onChanged` الذي يستدعي `setState`، وكذلك فحص `mounted` لمعرفة ما إذا كانت الشاشة ما زالت موجودة.

وجوده داخل `home` مقصود: البيانات الأساسية تأتي مجمّعة من `/api/bootstrap`، وتشترك الأقسام في حالة التحميل والتحديث والفلاتر. شاشات الوظائف تستقبل هذا الـ Controller صراحةً.

## 6. انتقال البيانات

مثال تحميل مساحة العمل:

```text
WorkspaceScreen
    -> WorkspaceController.load()
    -> WorkspaceRepository.loadWorkspace()
    -> PathwayApi.request('/api/bootstrap')
    -> الخادم
    -> تحديث controller.data
    -> onChanged()
    -> setState() وإعادة بناء الواجهة
```

`WorkspaceRepository` يوفّر عمليات مثل تحميل مساحة العمل وجلب عميل وإرسال نموذج وإكمال مهمة. أما `PathwayApi` فينفّذ HTTP ويضيف رمز الجلسة ويحوّل JSON ويعالج أخطاء الاتصال.

مسار تسجيل الدخول منفصل: `LoginScreen` يستخدم `LoginController`، الذي يعتمد على `AuthenticationService` للوصول إلى `PathwayApi`.

## 7. التنقل والنماذج

`lib/core/routes/workspace_routes.dart` يختار الشاشة بناءً على `controller.section`. التنقل الحالي قائم على الأقسام، وشريط التنقل السفلي موجود في `WorkspaceScreen`.

`WorkspaceFormPresenter` داخل `home/widgets/` ينسّق عرض النماذج في النوافذ السفلية. تعريفات النماذج موزعة حسب الوظيفة:

| الملف داخل `lib/features/` | المسؤولية |
| --- | --- |
| `leads/widgets/lead_forms.dart` | نماذج العملاء. |
| `planner/widgets/activity_forms.dart` | نماذج الأنشطة. |
| `inbox/widgets/email_forms.dart` | نماذج البريد. |
| `applications/widgets/application_forms.dart` | نماذج الطلبات. |
| `profile/widgets/team_forms.dart` | نماذج الفريق. |

`shared/widgets/action_form.dart` هو عنصر النموذج المشترك، و`shared/components/form_field_spec.dart` يصف حقوله. وصف الحقل إعداد للواجهة، وليس Model لبيانات العمل.

## 8. الأجزاء المشتركة والخدمات

| المكان | المسؤولية |
| --- | --- |
| `core/constants/` | ألوان التطبيق. |
| `core/theme/` | إعداد الثيم. |
| `core/errors/` | تعريف `ApiException`. |
| `core/utils/` | دوال مساعدة للبيانات والأسماء والتواريخ. |
| `shared/widgets/` | عناصر قابلة لإعادة الاستخدام مثل `StatusBadge` و`SectionCard` و`Notice` و`EmptyState` و`PersonAvatar`. |
| `services/storage/session_storage.dart` | حفظ رمز الجلسة وقراءته وحذفه باستخدام التخزين الآمن، بمفتاح مرتبط بعنوان الخادم. |
| `services/storage/evidence_file_service.dart` | اختيار المستندات وتنزيلها وفتح الملفات المؤقتة وتنظيفها. |

نماذج البيانات مثل `LeadRecord` و`TaskRecord` و`ApplicationRecord` موجودة داخل وظائفها. `WorkspaceSnapshot` يسهّل قراءة بيانات مساحة العمل، و`workspace_models.dart` يعيد تصدير النماذج للتوافق. ما زال الـ Controller يحتفظ بالبيانات الأساسية بصيغة `Map<String, dynamic>`.

## 9. الملفات خارج lib

| المكان | دوره |
| --- | --- |
| `test/` | اختبارات تسجيل الدخول ومساحة العمل والتنقل والنماذج والبيانات. |
| `test/support/fake_pathway_api.dart` | API وهمي للاختبارات دون خادم فعلي. |
| `android/` و`ios/` | ملفات تشغيل وإعداد المنصتين الأصليتين. |
| `web/` و`windows/` و`linux/` و`macos/` | ملفات المنصات الأخرى الموجودة بالمشروع؛ وجودها لا يعني أن كل تكامل تم اختباره عليها. |
| `pubspec.yaml` | تعريف المشروع والمكتبات وإعدادات الموارد. |
| `docs/` | توثيق المشروع. |
| `build/` و`.dart_tool/` | ملفات مولّدة بواسطة أدوات التطوير والبناء. |

## 10. أعدّل فين؟

| التعديل المطلوب | المكان المناسب |
| --- | --- |
| تغيير عنوان الخادم | `config/app_config.dart` أو قيمة `--dart-define` وقت التشغيل. |
| تغيير الألوان أو الثيم | `core/constants/app_colors.dart` و`core/theme/app_theme.dart`. |
| تعديل شاشة العملاء | `features/leads/screens/`. |
| تعديل البحث أو الفلاتر المشتركة | `features/home/controllers/workspace_controller.dart`. |
| إضافة عملية بيانات لمساحة العمل | `features/home/repositories/workspace_repository.dart` ثم استدعاؤها من الـ Controller. |
| تعديل النقل أو معالجة HTTP | `services/api/pathway_api.dart`. |
| إضافة نموذج | ملف النماذج داخل `widgets/` للوظيفة المعنية. |
| إضافة عنصر تستخدمه عدة وظائف | `shared/widgets/`. |
| إضافة قسم جديد | شاشة داخل الوظيفة، ثم ربطها في `core/routes/workspace_routes.dart` وإضافة مدخل الوصول المناسب في الواجهة. |

بعد تعديل الكود، أوامر التحقق المعتادة من جذر المشروع هي:

```sh
flutter analyze
flutter test
flutter build apk --debug
```

هذه أوامر للاستخدام عند التطوير؛ إنشاء ملف الشرح نفسه لا يعني تنفيذها أو إعادة التحقق من تكامل الخادم والأجهزة.
