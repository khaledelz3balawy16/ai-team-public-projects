# PMP Exam Blueprint Decision

## Why the platform uses 3 official domains and 7 practice domains

The PMP simulator has two different classification layers because they solve two different product problems.

## 1. Official exam blueprint: 3 domains

The full PMP mock exam should follow PMI's official exam structure:

- People: 33%
- Process: 41%
- Business Environment: 26%
- Full mock length: 180 questions
- Time limit: 240 minutes

This layer is used for the full exam simulator because it makes the mock exam defensible, explainable, and aligned with how the real PMP exam is positioned.

## 2. Learning and diagnosis map: 7 practice domains

The platform also keeps seven learner-facing practice domains:

- Governance
- Scope
- Schedule
- Finance
- Stakeholders
- Resources
- Risk

These are not meant to replace PMI's official three-domain blueprint. They are used to help learners understand exactly what to improve after practice.

A three-domain score is useful for exam alignment, but it is too broad for coaching. For example, a weak Process score does not tell the learner whether the real gap is schedule control, procurement, risk response, scope change control, or financial decision-making. The seven-domain layer gives the AI coach enough detail to generate focused recommendations and learning chapters.

## Mapping used by the platform

For the production simulator, questions are sampled into the official PMP domains using this internal mapping:

- People: Stakeholders, Resources
- Process: Scope, Schedule, Finance, Risk
- Business Environment: Governance

If a question is explicitly tagged with an official domain such as People, Process, or Business Environment, that tag can be used. Otherwise, the system safely infers the official domain from the seven-domain practice taxonomy.

## Product rationale

This design gives us both:

- Exam realism: the full mock follows the official PMP 3-domain weighting.
- Better coaching: the learner gets detailed weak-area diagnosis across seven practical skill areas.
- Better AI reports: chapters and study plans can target narrow gaps instead of vague domain labels.
- Better sales story: the product can be positioned as an official-style PMP simulator plus a personal readiness coach.

## How to explain it simply

We use the official three PMP domains to build the exam, and the seven internal domains to teach the student. The three-domain model keeps the simulator aligned with PMI. The seven-domain model makes feedback actionable.
