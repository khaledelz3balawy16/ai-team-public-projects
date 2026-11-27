# Exam Types Expansion

Goal: exams should not be limited to domain-based practice. Add a first-class
`examType` selector and make `domainId` optional depending on the selected type.

## Suggested exam types

```ts
export type ExamType =
  | "domain"
  | "full_mock"
  | "mini_mock"
  | "knowledge_area"
  | "process_group"
  | "difficulty"
  | "weak_areas"
  | "wrong_questions"
  | "bookmarked"
  | "random_practice"
  | "timed_drill"
  | "custom";
```

## Request shape

```ts
export type CreateExamRequest = {
  examType: ExamType;
  questionCount?: number;
  durationMinutes?: number;
  domainId?: string;
  knowledgeAreaId?: string;
  processGroupId?: string;
  difficulty?: "easy" | "medium" | "hard" | "mixed";
  includeOnlyBookmarked?: boolean;
  includeOnlyWrong?: boolean;
  includeWeakAreas?: boolean;
  domainIds?: string[];
  knowledgeAreaIds?: string[];
  processGroupIds?: string[];
};
```

## Default behavior

```ts
export const EXAM_TYPE_DEFAULTS: Record<ExamType, {
  label: string;
  questionCount: number;
  durationMinutes?: number;
}> = {
  domain: { label: "Domain Practice", questionCount: 30 },
  full_mock: { label: "Full Mock Exam", questionCount: 180, durationMinutes: 230 },
  mini_mock: { label: "Mini Mock", questionCount: 30, durationMinutes: 40 },
  knowledge_area: { label: "Knowledge Area", questionCount: 30 },
  process_group: { label: "Process Group", questionCount: 30 },
  difficulty: { label: "Difficulty Drill", questionCount: 25 },
  weak_areas: { label: "Weak Areas", questionCount: 25 },
  wrong_questions: { label: "Wrong Questions", questionCount: 25 },
  bookmarked: { label: "Bookmarked Questions", questionCount: 25 },
  random_practice: { label: "Random Practice", questionCount: 30 },
  timed_drill: { label: "Timed Drill", questionCount: 20, durationMinutes: 20 },
  custom: { label: "Custom Exam", questionCount: 30 },
};
```

## Filtering rules

```ts
function buildQuestionFilter(input: CreateExamRequest, userId: string) {
  switch (input.examType) {
    case "domain":
      return { domainId: input.domainId };
    case "knowledge_area":
      return { knowledgeAreaId: input.knowledgeAreaId };
    case "process_group":
      return { processGroupId: input.processGroupId };
    case "difficulty":
      return { difficulty: input.difficulty };
    case "weak_areas":
      return { userId, weakOnly: true };
    case "wrong_questions":
      return { userId, wrongOnly: true };
    case "bookmarked":
      return { userId, bookmarkedOnly: true };
    case "full_mock":
      return { balanced: true };
    case "mini_mock":
      return { balanced: true };
    case "random_practice":
      return {};
    case "timed_drill":
      return { timed: true };
    case "custom":
      return {
        domainIds: input.domainIds,
        knowledgeAreaIds: input.knowledgeAreaIds,
        processGroupIds: input.processGroupIds,
        difficulty: input.difficulty,
      };
  }
}
```

## UI notes

- Replace the domain-only entry point with an exam type grid or tabs.
- Show domain picker only when `examType === "domain"` or custom includes domains.
- Show knowledge area picker only for `knowledge_area` or custom.
- Show process group picker only for `process_group` or custom.
- Show difficulty picker for `difficulty` and custom.
- Disable `wrong_questions`, `bookmarked`, and `weak_areas` if the user has no matching questions yet.
