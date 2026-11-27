export interface ScoreItem {
  mean: number;
  level: string;
}

export interface AssessmentBlock {
  scores?: Record<string, ScoreItem>;
  [key: string]: unknown;
}

export interface AssessmentData {
  wellbeing:      AssessmentBlock;
  psychological:  AssessmentBlock;
  personality:    AssessmentBlock;
  career:         AssessmentBlock;
  riasec:         AssessmentBlock;
  ei:             AssessmentBlock;
  work:           AssessmentBlock;
  cognitive:      AssessmentBlock;
  logical:        AssessmentBlock;
  knowledge:      AssessmentBlock;
  skills:         AssessmentBlock;
  behaviors:      AssessmentBlock;
  learning_style: AssessmentBlock;
}

export interface CareerGate {
  completed:    number;
  minRequired:  number;
  canShow:      boolean;
  alreadyToday: boolean;
  data:         CareerItem[] | null;
  skills:       string[] | null;
}

export interface CareerItem {
  title:       string;
  description: string;
  icon?:       { name: string; style?: string };
}

export interface DashboardUser {
  email:    string;
  name:     string;
}

export interface DashboardResponse {
  user:                 DashboardUser;
  assessment_data:      AssessmentData;
  career_gate:          CareerGate;
  can_start_new_cycle:  boolean;
}
