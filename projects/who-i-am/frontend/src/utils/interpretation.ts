import type { AssessmentBlock, ScoreItem } from '../types/assessment';

const DIM_LABELS: Record<string, Record<string, string>> = {
  wellbeing: {
    depression:    'depression resilience',
    anxiety:       'anxiety management',
    stress:        'stress management',
    sleep_quality: 'sleep quality',
  },
  psychological: {
    hope:             'hope',
    efficacy:         'self-efficacy',
    psych_resilience: 'resilience',
    optimism:         'optimism',
    gratitude:        'gratitude',
  },
  personality: {
    openness:          'openness',
    conscientiousness: 'conscientiousness',
    extraversion:      'extraversion',
    agreeableness:     'agreeableness',
    neuroticism:       'neuroticism',
  },
  career: {
    autonomy:         'career autonomy',
    adaptability:     'adaptability',
    career_resilience:'personal resilience',
    identity:         'career identity',
  },
  riasec: {
    realistic:     'Realistic',
    investigative: 'Investigative',
    artistic:      'Artistic',
    social:        'Social',
    enterprising:  'Enterprising',
    conventional:  'Conventional',
  },
  ei: {
    self_awareness:        'self-awareness',
    self_management:       'self-management',
    social_awareness:      'social awareness',
    relationship_management: 'relationship management',
  },
  work: {
    achievement:        'achievement',
    independence:       'independence',
    recognition:        'recognition',
    relationships:      'relationships',
    support:            'support',
    working_conditions: 'working conditions',
  },
  cognitive: {
    sentence_correction:    'sentence correction',
    critical_reasoning:     'critical reasoning',
    reading_comprehension:  'reading comprehension',
    verbal_intelligence:    'verbal intelligence',
    memory_cognitive_speed: 'memory & cognitive speed',
  },
  logical: {
    arithmetic:          'arithmetic',
    algebra:             'algebra',
    geometry:            'geometry',
    data_interpretation: 'data interpretation',
    numerical_reasoning: 'numerical reasoning',
  },
  knowledge: {
    marketing_concepts: 'marketing concepts',
    business_awareness: 'business awareness',
    market_research:    'market research',
    products_channels:  'products & channels',
    digital_marketing:  'digital marketing',
  },
  skills: {
    campaign_planning:  'campaign planning',
    communication:      'communication',
    project_management: 'project management',
    data_analysis:      'data analysis',
    marketing_tools:    'marketing tools',
  },
  behaviors: {
    agility_adaptability:   'agility & adaptability',
    creativity_innovation:  'creativity & innovation',
    collaboration_teamwork: 'collaboration & teamwork',
  },
};

function levelWord(level: string): string {
  return (level || '').toLowerCase();
}

function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function buildInterpretation(quizType: string, block: AssessmentBlock): string {
  const scores = (block.scores ?? {}) as Record<string, ScoreItem>;
  const entries = Object.entries(scores).filter(([, v]) => v && typeof v.mean === 'number');

  if (!entries.length) {
    return 'Complete this assessment to see your personalised interpretation.';
  }

  const sorted = [...entries].sort(([, a], [, b]) => b.mean - a.mean);
  const [topKey, topScore] = sorted[0];
  const [bottomKey, bottomScore] = sorted[sorted.length - 1];

  const overallKey = `overall_${quizType}`;
  const overall = block[overallKey] as ScoreItem | undefined;
  const overallLevel = overall?.level ?? topScore.level;

  const dimLabels = DIM_LABELS[quizType] ?? {};
  const topName    = dimLabels[topKey]    ?? topKey.replace(/_/g, ' ');
  const bottomName = dimLabels[bottomKey] ?? bottomKey.replace(/_/g, ' ');

  switch (quizType) {
    case 'wellbeing': {
      const anxiety  = scores['anxiety']?.level  ?? '';
      const stress   = scores['stress']?.level   ?? '';
      const sleep    = scores['sleep_quality']?.level ?? '';
      const concerns: string[] = [];
      if (['Low', 'Very Low'].includes(anxiety))  concerns.push('anxiety');
      if (['Low', 'Very Low'].includes(stress))   concerns.push('stress management');
      if (['Low', 'Very Low'].includes(sleep))    concerns.push('sleep quality');
      const goodSleep = ['High', 'Very High'].includes(sleep);
      if (concerns.length) {
        return `Your overall wellbeing is ${levelWord(overallLevel)}. ${capitalize(concerns.join(' and '))} ${concerns.length > 1 ? 'are areas' : 'is an area'} to watch — consider support strategies to improve them. ${goodSleep ? 'Your sleep quality is a positive strength.' : ''}`.trim();
      }
      return `Your overall wellbeing is ${levelWord(overallLevel)}. Your strongest dimension is ${topName} and your ${bottomName} has the most room for growth. Keep maintaining healthy routines.`;
    }

    case 'psychological':
      return `Your overall psychological capital is ${levelWord(overallLevel)}. ${capitalize(topName)} is your greatest strength (${levelWord(topScore.level)}). Focus on building ${bottomName} (${levelWord(bottomScore.level)}) through goal-setting and positive self-talk.`;

    case 'personality':
      return `Your personality profile shows ${levelWord(topScore.level)} ${topName}, which is a key strength for structured and creative work. Your ${bottomName} score (${levelWord(bottomScore.level)}) reflects a natural preference you can channel effectively in the right roles.`;

    case 'career':
      return `Your career adaptability is ${levelWord(overallLevel)}. ${capitalize(topName)} is your top strength (${levelWord(topScore.level)}), showing you are ready to navigate career changes. Strengthening ${bottomName} (${levelWord(bottomScore.level)}) will further boost your career readiness.`;

    case 'riasec': {
      const top2 = sorted.slice(0, 2).map(([k]) => dimLabels[k] ?? k);
      return `Your strongest career interests are ${top2[0]} and ${top2[1]}, suggesting you are well-suited for roles that involve ${top2[0].toLowerCase()}-oriented and ${top2[1].toLowerCase()}-oriented activities. Your overall profile is ${levelWord(overallLevel)}.`;
    }

    case 'ei':
      return `Your emotional intelligence is ${levelWord(overallLevel)}. ${capitalize(topName)} is your standout strength (${levelWord(topScore.level)}). Developing ${bottomName} (${levelWord(bottomScore.level)}) will help you become a more well-rounded communicator and leader.`;

    case 'work':
      return `Your work values profile is ${levelWord(overallLevel)} overall. You place the highest value on ${topName} (${levelWord(topScore.level)}), which will guide your ideal work environment. ${capitalize(bottomName)} is valued less, suggesting you may thrive in roles that prioritise autonomy over ${bottomName}.`;

    case 'cognitive':
      return `Your English and cognitive skills are ${levelWord(overallLevel)} overall. ${capitalize(topName)} is your strongest area (${levelWord(topScore.level)}). Practising ${bottomName} (${levelWord(bottomScore.level)}) will help you build a more balanced cognitive profile.`;

    case 'logical':
      return `Your mathematical and logical reasoning is ${levelWord(overallLevel)} overall. ${capitalize(topName)} is your top skill (${levelWord(topScore.level)}). Targeted practice in ${bottomName} (${levelWord(bottomScore.level)}) will strengthen your overall numeracy.`;

    case 'knowledge':
      return `Your marketing knowledge is ${levelWord(overallLevel)} overall. You show the strongest understanding in ${topName} (${levelWord(topScore.level)}). Deepening your knowledge of ${bottomName} (${levelWord(bottomScore.level)}) will round out your professional expertise.`;

    case 'skills':
      return `Your marketing skills are ${levelWord(overallLevel)} overall. ${capitalize(topName)} is your key practical strength (${levelWord(topScore.level)}). Building ${bottomName} (${levelWord(bottomScore.level)}) will make you a more versatile marketing professional.`;

    case 'behaviors':
      return `Your professional behaviours are ${levelWord(overallLevel)} overall. ${capitalize(topName)} stands out as your defining behaviour (${levelWord(topScore.level)}). Developing ${bottomName} (${levelWord(bottomScore.level)}) will make you an even stronger team contributor.`;

    default:
      return `Your ${quizType} score is ${levelWord(overallLevel)}. Your strongest dimension is ${topName} and your area for most growth is ${bottomName}.`;
  }
}
