import { useEffect, useState } from 'react';
import { useDashboard } from '../hooks/useDashboard';
import { AssessmentCard } from '../components/AssessmentCard';
import { LearningStyle }  from '../components/LearningStyle';
import { CareerPath }     from '../components/CareerPath';
import { QuizModal }      from '../components/QuizModal';

const SECTIONS = [
  {
    title: 'Wellbeing Assessment',
    chartId: 'wellbeingChart',
    sectionId: 'wellbeingSection',
    blockKey: 'wellbeing' as const,
    overallKey: 'overall_wellbeing',
    quizType: 'wellbeing',
    interpretation: 'Your wellbeing scores indicate moderate stress levels balanced by good sleep quality. Consider stress management techniques to improve your overall wellbeing.',
    scoreDefs: [
      { key: 'depression',   label: 'Depression' },
      { key: 'anxiety',      label: 'Anxiety' },
      { key: 'stress',       label: 'Stress' },
      { key: 'sleep_quality',label: 'Sleep Quality' },
    ],
  },
  {
    title: 'Psychological Capital',
    chartId: 'psychCapitalChart',
    sectionId: 'PsychologicalCapital',
    blockKey: 'psychological' as const,
    overallKey: 'overall_psychological',
    quizType: 'psychological',
    interpretation: 'You show strong resilience and optimism, which are valuable traits for academic success. Your hope and efficacy scores indicate room for growth in goal-setting and self-belief.',
    scoreDefs: [
      { key: 'hope',             label: 'Hope' },
      { key: 'efficacy',         label: 'Efficacy' },
      { key: 'psych_resilience', label: 'Resilience' },
      { key: 'optimism',         label: 'Optimism' },
      { key: 'gratitude',        label: 'Gratitude' },
    ],
  },
  {
    title: 'Personality Traits',
    chartId: 'personalityChart',
    sectionId: 'personalitySection',
    blockKey: 'personality' as const,
    overallKey: 'overall_personality',
    quizType: 'personality',
    interpretation: 'Your personality profile shows high openness to new experiences and conscientiousness, making you well-suited for creative yet structured work.',
    scoreDefs: [
      { key: 'openness',          label: 'Openness' },
      { key: 'conscientiousness', label: 'Conscientiousness' },
      { key: 'extraversion',      label: 'Extraversion' },
      { key: 'agreeableness',     label: 'Agreeableness' },
      { key: 'neuroticism',       label: 'Neuroticism' },
    ],
  },
  {
    title: 'Career Adaptability',
    chartId: 'careerChart',
    sectionId: 'careerSection',
    blockKey: 'career' as const,
    overallKey: 'overall_career',
    quizType: 'career',
    interpretation: 'You demonstrate strong career autonomy and adaptability, showing you\'re prepared to navigate changing work environments.',
    scoreDefs: [
      { key: 'autonomy',          label: 'Career Autonomy' },
      { key: 'adaptability',      label: 'Adaptability' },
      { key: 'career_resilience', label: 'Personal Resilience' },
      { key: 'identity',          label: 'Identity' },
    ],
  },
  {
    title: 'Career Interests (RIASEC)',
    chartId: 'riasecChart',
    sectionId: 'riasecSection',
    blockKey: 'riasec' as const,
    overallKey: 'overall_riasec',
    quizType: 'riasec',
    interpretation: 'Your RIASEC profile shows strong interests in Social and Enterprising activities, suggesting you would excel in roles involving leadership, persuasion, and helping others.',
    scoreDefs: [
      { key: 'realistic',     label: 'Realistic' },
      { key: 'investigative', label: 'Investigative' },
      { key: 'artistic',      label: 'Artistic' },
      { key: 'social',        label: 'Social' },
      { key: 'enterprising',  label: 'Enterprising' },
      { key: 'conventional',  label: 'Conventional' },
    ],
  },
  {
    title: 'Emotional Intelligence (EI)',
    chartId: 'eiChart',
    sectionId: 'eiSection',
    blockKey: 'ei' as const,
    overallKey: 'overall_ei',
    quizType: 'ei',
    interpretation: 'Your EI profile indicates strong self-awareness and relationship management skills. These strengths will serve you well in leadership roles.',
    scoreDefs: [
      { key: 'self_awareness',         label: 'Self-Awareness' },
      { key: 'self_management',        label: 'Self-Management' },
      { key: 'social_awareness',       label: 'Social Awareness' },
      { key: 'relationship_management',label: 'Relationship Management' },
    ],
  },
  {
    title: 'Work Values',
    chartId: 'workValuesChart',
    sectionId: 'workValuesSection',
    blockKey: 'work' as const,
    overallKey: 'overall_work',
    quizType: 'work',
    interpretation: 'Your work values profile shows a strong emphasis on achievement and independence, with a balanced appreciation for relationships and support.',
    scoreDefs: [
      { key: 'achievement',       label: 'Achievement' },
      { key: 'independence',      label: 'Independence' },
      { key: 'recognition',       label: 'Recognition' },
      { key: 'relationships',     label: 'Relationships' },
      { key: 'support',           label: 'Support' },
      { key: 'working_conditions',label: 'Working Conditions' },
    ],
  },
  {
    title: 'English & Cognitive Skills',
    chartId: 'englishCognitiveChart',
    sectionId: 'englishCognitiveSection',
    blockKey: 'cognitive' as const,
    overallKey: 'overall_cognitive',
    quizType: 'cognitive',
    interpretation: 'Your English and cognitive skills profile shows strong performance in critical reasoning and verbal intelligence.',
    scoreDefs: [
      { key: 'sentence_correction',  label: 'Sentence Correction' },
      { key: 'critical_reasoning',   label: 'Critical Reasoning' },
      { key: 'reading_comprehension',label: 'Reading Comprehension' },
      { key: 'verbal_intelligence',  label: 'Verbal Intelligence' },
      { key: 'memory_cognitive_speed',label: 'Memory & Cognitive Speed' },
    ],
  },
  {
    title: 'Mathematics & Logical Skills',
    chartId: 'mathLogicalChart',
    sectionId: 'mathLogicalSection',
    blockKey: 'logical' as const,
    overallKey: 'overall_logical',
    quizType: 'logical',
    interpretation: 'Your mathematical and logical reasoning abilities are well-balanced, with particular strengths in data interpretation and numerical reasoning.',
    scoreDefs: [
      { key: 'arithmetic',          label: 'Arithmetic' },
      { key: 'algebra',             label: 'Algebra' },
      { key: 'geometry',            label: 'Geometry' },
      { key: 'data_interpretation', label: 'Data Interpretation' },
      { key: 'numerical_reasoning', label: 'Numerical Reasoning' },
    ],
  },
  {
    title: 'Knowledge Assessment',
    chartId: 'knowledgeChart',
    sectionId: 'knowledgeSection',
    blockKey: 'knowledge' as const,
    overallKey: 'overall_knowledge',
    quizType: 'knowledge',
    interpretation: 'Your knowledge profile shows strong understanding of digital marketing and market research.',
    scoreDefs: [
      { key: 'marketing_concepts', label: 'Marketing Concepts' },
      { key: 'business_awareness', label: 'Business Awareness' },
      { key: 'market_research',    label: 'Market Research' },
      { key: 'products_channels',  label: 'Products & Channels' },
      { key: 'digital_marketing',  label: 'Digital Marketing' },
    ],
  },
  {
    title: 'Skills Assessment',
    chartId: 'skillsChart',
    sectionId: 'skillsSection',
    blockKey: 'skills' as const,
    overallKey: 'overall_skills',
    quizType: 'skills',
    interpretation: 'Your skills profile demonstrates excellence in communication and campaign planning.',
    scoreDefs: [
      { key: 'campaign_planning',  label: 'Campaign Planning' },
      { key: 'communication',      label: 'Communication' },
      { key: 'project_management', label: 'Project Management' },
      { key: 'data_analysis',      label: 'Data Analysis' },
      { key: 'marketing_tools',    label: 'Marketing Tools' },
    ],
  },
  {
    title: 'Behaviors Assessment',
    chartId: 'behaviorsChart',
    sectionId: 'behaviorsSection',
    blockKey: 'behaviors' as const,
    overallKey: 'overall_behaviors',
    quizType: 'behaviors',
    interpretation: 'Your behavioral profile shows exceptional creativity and innovation, with strong teamwork abilities.',
    scoreDefs: [
      { key: 'agility_adaptability',   label: 'Agility & Adaptability' },
      { key: 'creativity_innovation',  label: 'Creativity & Innovation' },
      { key: 'collaboration_teamwork', label: 'Collaboration & Teamwork' },
    ],
  },
] as const;

const TABS = [
  { label: 'Mental Well-Being',          anchor: 'mentalWellbeingSection' },
  { label: 'Psychometric & Aptitude',    anchor: 'PsychologicalCapital' },
  { label: 'Knowledge, Skills & Behaviors', anchor: 'ksbs' },
];

const RETURN_SECTION_MAP: Record<string, string> = {
  wellbeing: 'mentalWellbeingSection',
  psychological: 'PsychologicalCapital',
  personality: 'personalitySection',
  career: 'careerSection',
  riasec: 'riasecSection',
  ei: 'eiSection',
  work: 'workValuesSection',
  cognitive: 'ksbs',
  logical: 'mathLogicalSection',
  knowledge: 'knowledgeSection',
  skills: 'skillsSection',
  behaviors: 'behaviorsSection',
  learning_style: 'learningStyleSection',
};

export function Dashboard() {
  const { data, loading, error, refetch } = useDashboard();
  const [activeTab, setActiveTab]     = useState(0);
  const [quizType,  setQuizType]      = useState<string | null>(null);
  const [careerRefresh, setCareerRefresh] = useState(0);

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  useEffect(() => {
    if (loading || error) return;

    const params = new URLSearchParams(window.location.search);
    if (params.get('from_quiz') !== '1') return;

    const type = (params.get('type') || '').toLowerCase();
    const sectionId = RETURN_SECTION_MAP[type];
    if (!sectionId) return;

    window.setTimeout(() => {
      scrollTo(sectionId);
      const sectionEl = document.getElementById(sectionId);
      sectionEl?.classList.add('return-highlight');
      window.setTimeout(() => sectionEl?.classList.remove('return-highlight'), 2500);
    }, 150);
  }, [loading, error]);

  if (loading) return (
    <div className="loading-screen">
      <div className="spinner" />
      <p>Loading your dashboard…</p>
    </div>
  );

  if (error) return (
    <div className="error-screen">
      <p>Could not load dashboard. Please refresh the page.</p>
    </div>
  );

  const { user, assessment_data, career_gate } = data!;

  return (
    <div id="psycho-dashboard">
      {/* Header */}
      <section className="page-header">
        <div className="container">
          <div className="header-row">
            <div>
              <h1>Who I Am</h1>
              <p>Discover your personality profile, learning style, and strengths</p>
            </div>
            <a href="/student-dashboard/" className="btn-back">← Back to Your Dashboard</a>
          </div>
        </div>
      </section>

      <section className="py-8">
        <div className="container">
          {/* User info */}
          <div className="user-card">
            <div>
              <h2>{user.name}</h2>
              <p className="user-email">{user.email}</p>
            </div>
          </div>

          {/* Tab nav */}
          <div className="tab-nav">
            {TABS.map((tab, i) => (
              <button
                key={tab.anchor}
                className={`tab-button ${activeTab === i ? 'active' : ''}`}
                onClick={() => { setActiveTab(i); scrollTo(tab.anchor); }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Mental Well-Being */}
          <div id="mentalWellbeingSection" className="section-anchor" />
          {SECTIONS.slice(0, 7).map(s => (
            <AssessmentCard
              key={s.chartId}
              {...s}
              id={s.sectionId}
              block={assessment_data[s.blockKey]}
              onStartQuiz={setQuizType}
            />
          ))}

          {/* KSBs */}
          <div id="ksbs" className="section-anchor" />
          {SECTIONS.slice(7).map(s => (
            <AssessmentCard
              key={s.chartId}
              {...s}
              id={s.sectionId}
              block={assessment_data[s.blockKey]}
              onStartQuiz={setQuizType}
            />
          ))}

          {/* Learning Style + Career */}
          <div className="two-col-grid">
            <LearningStyle
              block={assessment_data.learning_style}
              onStartQuiz={setQuizType}
            />
            <CareerPath
              key={careerRefresh}
              gate={career_gate}
              assessmentData={assessment_data}
              isRawan={user.is_rawan}
              onShown={() => setCareerRefresh(r => r + 1)}
            />
          </div>
        </div>
      </section>

      <QuizModal
        quizType={quizType}
        onClose={() => setQuizType(null)}
        onSaved={() => void refetch()}
      />
    </div>
  );
}
