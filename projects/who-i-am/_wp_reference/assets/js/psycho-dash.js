/* =====================================================
   psycho-dash.js (FULL CLEAN VERSION)
   - Radar uses mean (0..5) so values are correct
   - Tooltip shows mean + level for each axis
   - RAG bars move by level (Low/Moderate/High/...) and show level + mean
===================================================== */

/* ===============================
   Helpers
================================ */

function hideById(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.display = 'none';
}


let selectedQuizType = null;

window.CAREER_WEBHOOK_URL = "https://n8n.srv943390.hstgr.cloud/webhook/2bbf6b68-1fd2-4ece-a78c-5c622a9584d4-psychological";

function toNumber(x) {
  const n = parseFloat(x);
  return Number.isFinite(n) ? n : 0;
}

function formatMean(mean) {
  return toNumber(mean).toFixed(1);
}

function levelColor(level) {
  switch ((level || '').toLowerCase()) {
    case 'very high':
    case 'high':
    case 'good':
      return '#16a34a';
    case 'moderate':
    case 'medium':
      return '#f59e0b';
    case 'low':
    case 'poor':
      return '#dc2626';
    default:
      return '#2563eb';
  }
}

function levelToPercent(level) {
  switch ((level || '').toLowerCase()) {
    case 'very high': return 95;
    case 'high':
    case 'good':      return 80;
    case 'moderate':
    case 'medium':    return 55;
    case 'low':
    case 'poor':      return 25;
    case 'very low':  return 10;
    default:          return 0;
  }
}

function getScores(block) {
  if (!block) return {};
  if (block.scores && typeof block.scores === 'object') return block.scores;
  return block;
}

/* ===============================
   Career Helpers + Career Path Logic (CLEAN)
================================ */

/* ---------- Resolve User ONCE ---------- */
document.addEventListener('DOMContentLoaded', () => {
  window.__PSYCHO_USER__ = {
    email: (window.PSYCHO?.user?.email || '').trim().toLowerCase() || null,
    name:  (window.PSYCHO?.user?.name  || '').trim() || null,
    login: (window.PSYCHO?.user?.login || '').trim().toLowerCase() || null
  };

  window.__IS_RAWAN__ =
    window.__PSYCHO_USER__.login === 'rawan' ||
    window.__PSYCHO_USER__.email === 'contact+be387083e60a@example.com';

  // Debug (احذفيه بعد التأكد)
  console.log('Resolved user:', window.__PSYCHO_USER__, 'isRawan:', window.__IS_RAWAN__);
});

/* ---------- Return from Quiz → Focus Section (ROBUST) ---------- */
document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);

  if (params.get('from_quiz') !== '1') return;

  const type = (params.get('type') || '').toLowerCase();
  if (!type) return;

  const sectionMap = {
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
    learning_style: 'learningStyleSection'
  };

  const sectionId = sectionMap[type];
  if (!sectionId) return;

  // ⏳ استنى لحد ما الصفحة + الرسومات تخلص
  window.addEventListener('load', () => {
    const sectionEl = document.getElementById(sectionId);
    if (!sectionEl) return;

    sectionEl.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });

    // ✨ Highlight UX
    sectionEl.classList.add('ring-2', 'ring-primary', 'ring-offset-4');
    setTimeout(() => {
      sectionEl.classList.remove('ring-2', 'ring-primary', 'ring-offset-4');
    }, 2500);
  });
});




/* ---------- Career Data Helpers ---------- */
function parseCareerData(raw) {
  if (!raw) return null;
  if (typeof raw === 'string') {
    try { return JSON.parse(raw); } catch { return null; }
  }
  return raw;
}

function faIcon(icon) {
  if (!icon || !icon.name) return 'fa-solid fa-briefcase';
  const style = icon.style === 'brands' ? 'fa-brands' : 'fa-solid';
  return `${style} fa-${icon.name}`;
}

function renderCareerFromN8n(list) {
  const container = document.getElementById('careerCards');
  const skillsUl  = document.getElementById('careerSkills');
  const status    = document.getElementById('careerStatusText');

  if (!container || !Array.isArray(list)) {
    console.warn('Invalid career data', list);
    return;
  }

  container.innerHTML = '';
  if (skillsUl) skillsUl.innerHTML = '';
  if (status) status.textContent =
    'Based on your personality profile, learning style, and aptitude assessments, these career paths align well with your strengths:';

  list.forEach(item => {
    const card = document.createElement('div');
    card.className =
      'border border-gray-200 rounded-lg p-4 hover:border-primary transition-colors bg-white';

    card.innerHTML = `
      <div class="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center mb-3">
        <i class="${faIcon(item.icon)} text-primary"></i>
      </div>

      <h4 class="font-medium text-gray-900 mb-1">
        ${item.title}
      </h4>

      <p class="text-sm text-gray-600 leading-relaxed">
        ${item.description}
      </p>
    `;

    container.appendChild(card);
  });
}

function renderCareerSkills(data) {
  const ul = document.getElementById('careerSkills');
  if (!ul || !data?.skills_to_develop) return;

  ul.innerHTML = '';
  data.skills_to_develop.forEach(skill => {
    const li = document.createElement('li');
    li.className = 'flex items-start';
    li.innerHTML = `
      <i class="ri-arrow-right-line text-primary mr-2 mt-1"></i>
      <span>${skill}</span>
    `;
    ul.appendChild(li);
  });
}


/* ---------- Career Path Button Logic ---------- */
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('showCareerPathBtn');
  const section = document.getElementById('careerPathSection');
  if (!btn || !section || !window.CAREER_GATE) return;

  const { completed, minRequired, canShow, alreadyThisMonth } = window.CAREER_GATE;
  const { email: userEmail, name: userName, login: userLogin } = window.__PSYCHO_USER__;
  const isRawan = window.__IS_RAWAN__;

  // Already shown
  if (window.CAREER_GATE?.data) {
  section.classList.remove('hidden');

  renderCareerFromN8n(window.CAREER_GATE.data);

  if (window.CAREER_GATE.skills) {
    renderCareerSkills({ skills_to_develop: window.CAREER_GATE.skills });
  }

  // اقفلي الزر لغير Rawan فقط
  if (!isRawan) {
    btn.disabled = true;
  }
}

  // Not enough exams
  if (completed < minRequired || !canShow) {
    btn.disabled = true;
    return;
  }

  btn.disabled = false;

  btn.addEventListener('click', async () => {
  section.classList.remove('hidden');
//   if (!isRawan) btn.disabled = true;
  btn.disabled = true;
  btn.classList.add('opacity-60', 'cursor-wait');
  
  const status = document.getElementById('careerStatusText');
  const skillsWrapper = document.getElementById('careerSkillsWrapper');

  if (status) status.textContent = 'Generating your career path...';
  if (skillsWrapper) skillsWrapper.classList.add('hidden');

  try {
    const res = await fetch(window.CAREER_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source: 'career_path',
        user: {
          email: userEmail,
          name: userName,
          login: userLogin
        },
        assessment: window.ASSESSMENT_DATA || null
      })
    });

    const data = await res.json();
    console.log('Parsed n8n response:', data);

    const careers = Array.isArray(data)
      ? data
      : Array.isArray(data?.['Career recommendations'])
        ? data['Career recommendations']
        : Array.isArray(data?.career_recommendations)
          ? data.career_recommendations
          : [];

    // ===== Render (Optimistic UI) =====
    renderCareerFromN8n(careers);

    if (data?.skills_to_develop) {
      renderCareerSkills(data);
    }

    section.classList.remove('hidden');

    if (status) {
      status.textContent =
        'Based on your personality profile, learning style, and aptitude assessments, these career paths align well with your strengths:';
    }

    const skillsList = document.getElementById('careerSkills');
    if (skillsWrapper && skillsList && skillsList.children.length > 0) {
      skillsWrapper.classList.remove('hidden');
    }

    // 🔒 قفل الزر UX
    if (!isRawan) {
      btn.disabled = true;
      btn.classList.add('opacity-50', 'cursor-not-allowed');
    }

    // 💾 Save async في DB (بعد العرض)
try {
  await fetch(`${PSYCHO.restUrl}psycho/v1/career-path/save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-WP-Nonce': PSYCHO.nonce
    },
    body: JSON.stringify({
      career_recommendations: careers,
      skills_to_develop: data?.skills_to_develop || null
    })
  });
} catch (e) {
  console.error('Career path save failed:', e);
}

// ✅ بعد ما يخلص generate (UX)
if (isRawan) {
  btn.disabled = false;
  btn.classList.remove('opacity-60', 'cursor-wait');
}

  } catch (e) {
    console.error('n8n error:', e);
    if (status) status.textContent = 'Failed to generate career path. Please try again.';
  }
});
});

/* ===============================
   Tab Switcher
================================ */
document.addEventListener('DOMContentLoaded', function () {
  const tabButtons = document.querySelectorAll('.tab-button');
  tabButtons.forEach(button => {
    button.addEventListener('click', function () {
      tabButtons.forEach(btn => {
        btn.classList.remove('active', 'bg-primary', 'text-white');
        btn.classList.add('bg-gray-100', 'text-gray-700');
      });
      this.classList.add('active', 'bg-primary', 'text-white');
      this.classList.remove('bg-gray-100', 'text-gray-700');
    });
  });
});

/* ===============================
   Build-charts
================================ */

function percentToMean5(pct) {
  const p = Math.max(0, Math.min(100, Number(pct) || 0));
  return (p / 100) * 5;
}

function readScorePercentFromCard(cardEl, labelText) {
  if (!cardEl) return null;

  // يدور على span فيه اسم السكيل (مثلاً "Self-Awareness")
  const spans = Array.from(cardEl.querySelectorAll('span'));
  const labelSpan = spans.find(s => (s.textContent || '').trim().toLowerCase() === labelText.toLowerCase());
  if (!labelSpan) return null;

  // أقرب progress container بعده (div.bg-gray-200) وبعده inner bar
  const row = labelSpan.closest('div')?.parentElement; // div اللي فيه flex
  const barWrap = row?.nextElementSibling; // div.bg-gray-200
  const bar = barWrap?.querySelector('div'); // inner bar

  if (!bar) return null;

  // style="width: 85%"
  const w = (bar.style.width || '').trim();
  const pct = w.endsWith('%') ? parseFloat(w) : parseFloat(w);
  return Number.isFinite(pct) ? pct : null;
}

function buildScoresFromArrows(cardId, keys, labelsMap) {
  const card = document.getElementById(cardId);
  const out = {};
  keys.forEach(k => {
    const label = labelsMap[k];
    const pct = readScorePercentFromCard(card, label);
    if (pct == null) return;
    out[k] = { mean: percentToMean5(pct), level: '' };
  });
  return out;
}

/* ===============================
   Radar Charts
================================ */
document.addEventListener('DOMContentLoaded', function () {
  if (typeof echarts === 'undefined') return;

  const charts = [];
  const DATA = window.ASSESSMENT_DATA || {};

  function toNumber(x) {
    const n = parseFloat(x);
    return Number.isFinite(n) ? n : 0;
  }
  function formatMean(mean) {
    return toNumber(mean).toFixed(1);
  }
  function getScores(block) {
    if (!block) return {};
    if (block.scores && typeof block.scores === 'object') return block.scores;
    return block; // fallback لو متخزن بدون wrapper
  }

  function waitForSize(el, cb, tries = 120) {
    const w = el.clientWidth, h = el.clientHeight;
    if (w > 0 && h > 0) return cb();
    if (tries <= 0) return cb();
    requestAnimationFrame(() => waitForSize(el, cb, tries - 1));
  }

  function safeInit(id, option) {
    const el = document.getElementById(id);
    if (!el) return;

    if (el.clientHeight === 0) el.style.height = '260px';

    waitForSize(el, () => {
      const chart = echarts.init(el);
      chart.setOption(option, true);
      charts.push(chart);

      requestAnimationFrame(() => chart.resize());
      setTimeout(() => chart.resize(), 0);

      if ('ResizeObserver' in window) {
        const ro = new ResizeObserver(() => chart.resize());
        ro.observe(el);
      }
    });
  }

  function buildRadarOption({ keys, labels, scores, titleText }) {
    const values = keys.map(k => toNumber(scores?.[k]?.mean));

    return {
      title: titleText
        ? { text: titleText, left: 'center', top: 'bottom', textStyle: { fontSize: 12 } }
        : undefined,
      tooltip: {
        trigger: 'item',
        formatter: function () {
          return keys.map((k, i) => {
            const mean = scores?.[k]?.mean;
            const lvl  = scores?.[k]?.level || '';
            return `${labels[i]}: ${formatMean(mean)}${lvl ? ` (${lvl})` : ''}`;
          }).join('<br/>');
        }
      },
      radar: {
        indicator: labels.map(name => ({ name, max: 5 })),
        radius: 80,
        splitArea: { areaStyle: { color: ['#f8fafc'] } }
      },
      series: [{
        type: 'radar',
        symbol: 'circle',
        symbolSize: 6,
        data: [{
          name: 'Current',
          value: values,
          lineStyle: { color: '#2563eb', width: 2 },
          itemStyle: { color: '#2563eb' },
          areaStyle: { color: 'rgba(37, 99, 235, 0.25)' }
        }]
      }]
    };
  }

  // ✅ helper: نفس لوجيك Wellbeing لأي بلوك
  function meanToLevel(mean) {
  const m = Number(mean) || 0;
  if (m >= 4.2) return 'Very High';
  if (m >= 3.5) return 'High';
  if (m >= 2.5) return 'Moderate';
  if (m >= 1.5) return 'Low';
  return 'Very Low';
}

function computeOverall(scores, keys) {
  const vals = keys
    .map(k => Number(scores?.[k]?.mean))
    .filter(v => Number.isFinite(v)); // يشيل null/NaN

  if (!vals.length) return null;

  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  return { mean, level: meanToLevel(mean) };
}

// يجيب أي overall_* فيه mean/level
function pickOverallFromBlock(block, preferredKey) {
  if (!block || typeof block !== 'object') return null;

  // 1) لو preferredKey موجود استخدميه
  if (preferredKey && block[preferredKey] && block[preferredKey].mean != null) {
    return block[preferredKey];
  }

  // 2) دور على أول key يبدأ بـ overall_ وفيه mean
  const k = Object.keys(block).find(key =>
    key.startsWith('overall_') &&
    block[key] &&
    typeof block[key] === 'object' &&
    block[key].mean != null
  );

  return k ? block[k] : null;
}

function initRadar({ chartId, blockKey, overallKey, keys, labels }) {
  const block  = DATA[blockKey] || {};
  const scores = getScores(block);

  // ✅ هيلقط overall_riasec_profile / overall_work_values / ... إلخ
  let overall = pickOverallFromBlock(block, overallKey);

  // fallback حساب تلقائي لو مفيش overall في البلوك
  if (!overall) overall = computeOverall(scores, keys);

  safeInit(chartId, buildRadarOption({
    keys,
    labels,
    scores,
    titleText: overall?.mean != null
      ? `Overall: ${formatMean(overall.mean)}${overall.level ? ` (${overall.level})` : ''}`
      : ''
  }));
}


  // ===== WELLBEING =====
  initRadar({
    chartId: 'wellbeingChart',
    blockKey: 'wellbeing',
    overallKey: 'overall_wellbeing',
    keys: ['depression', 'anxiety', 'stress', 'sleep_quality'],
    labels: ['Depression', 'Anxiety', 'Stress', 'Sleep Quality']
  });

  // ===== PSYCHOLOGICAL =====
  initRadar({
    chartId: 'psychCapitalChart',
    blockKey: 'psychological',
    overallKey: 'overall_psychological',
    keys: ['hope', 'efficacy', 'psych_resilience', 'optimism', 'gratitude'],
    labels: ['Hope', 'Efficacy', 'Resilience', 'Optimism', 'Gratitude']
  });

  // ===== PERSONALITY =====
  initRadar({
    chartId: 'personalityChart',
    blockKey: 'personality',
    overallKey: 'overall_personality',
    keys: ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism'],
    labels: ['Openness', 'Conscientiousness', 'Extraversion', 'Agreeableness', 'Neuroticism']
  });

  // ===== CAREER =====
  initRadar({
    chartId: 'careerChart',
    blockKey: 'career',
    overallKey: 'overall_career',
    keys: ['autonomy', 'adaptability', 'career_resilience', 'identity'],
    labels: ['Career Autonomy', 'Adaptability', 'Resilience', 'Identity']
  });

  // ===== RIASEC =====
  initRadar({
    chartId: 'riasecChart',
    blockKey: 'riasec',
    overallKey: 'overall_riasec',
    keys: ['realistic', 'investigative', 'artistic', 'social', 'enterprising', 'conventional'],
    labels: ['Realistic', 'Investigative', 'Artistic', 'Social', 'Enterprising', 'Conventional']
  });

  // ===== EI =====
  initRadar({
    chartId: 'eiChart',
    blockKey: 'ei',
    overallKey: 'overall_ei',
    keys: ['self_awareness', 'self_management', 'social_awareness', 'relationship_management'],
    labels: ['Self-Awareness', 'Self-Management', 'Social Awareness', 'Relationship Management']
  });

  // ===== WORK VALUES =====
  initRadar({
    chartId: 'workValuesChart',
    blockKey: 'work',
    overallKey: 'overall_work',
    keys: ['achievement', 'independence', 'recognition', 'relationships', 'support', 'working_conditions'],
    labels: ['Achievement', 'Independence', 'Recognition', 'Relationships', 'Support', 'Working Conditions']
  });

  // ===== COGNITIVE (English) =====
  initRadar({
    chartId: 'englishCognitiveChart',
    blockKey: 'cognitive',
    overallKey: 'overall_cognitive',
    keys: ['sentence_correction', 'critical_reasoning', 'reading_comprehension', 'verbal_intelligence', 'memory_cognitive_speed'],
    labels: ['Sentence Correction', 'Critical Reasoning', 'Reading Comprehension', 'Verbal Intelligence', 'Memory Speed']
  });

  // ===== LOGICAL (Math) =====
  initRadar({
    chartId: 'mathLogicalChart',
    blockKey: 'logical',
    overallKey: 'overall_logical',
    keys: ['arithmetic', 'algebra', 'geometry', 'data_interpretation', 'numerical_reasoning'],
    labels: ['Arithmetic', 'Algebra', 'Geometry', 'Data Interpretation', 'Numerical Reasoning']
  });

  // ===== KNOWLEDGE =====
  initRadar({
    chartId: 'knowledgeChart',
    blockKey: 'knowledge',
    overallKey: 'overall_knowledge',
    keys: ['marketing_concepts', 'business_awareness', 'market_research', 'products_channels', 'digital_marketing'],
    labels: ['Marketing Concepts', 'Business Awareness', 'Market Research', 'Products & Channels', 'Digital Marketing']
  });

  // ===== SKILLS =====
  initRadar({
    chartId: 'skillsChart',
    blockKey: 'skills',
    overallKey: 'overall_skills',
    keys: ['campaign_planning', 'communication', 'project_management', 'data_analysis', 'marketing_tools'],
    labels: ['Campaign Planning', 'Communication', 'Project Management', 'Data Analysis', 'Marketing Tools']
  });

  // ===== BEHAVIORS =====
  initRadar({
    chartId: 'behaviorsChart',
    blockKey: 'behaviors',
    overallKey: 'overall_behaviors',
    keys: ['agility_adaptability', 'creativity_innovation', 'collaboration_teamwork'],
    labels: ['Agility & Adaptability', 'Creativity & Innovation', 'Collaboration & Teamwork']
  });


//   learning_style
const lsBlock = window.ASSESSMENT_DATA?.learning_style || {};
const ls = lsBlock.learning_styles || {};

const learningStyleData = [
  Number(ls.auditory?.percentage) || 0,
  Number(ls.visual?.percentage) || 0,
  Number(ls.reading_writing?.percentage) || 0,
  Number(ls.kinesthetic?.percentage) || 0
];

// Learning Style Chart
  const learningStyleOption = { animation:false, tooltip:{ trigger:'axis', axisPointer:{ type:'shadow' }, backgroundColor:'rgba(255,255,255,0.8)', borderColor:'#e2e8f0', textStyle:{ color:'#1f2937' } }, grid:{ top:10,right:30,bottom:30,left:90 }, xAxis:{ type:'value', max:100, axisLine:{ lineStyle:{ color:'#d1d5db' } }, axisLabel:{ color:'#1f2937', formatter:'{value}%' }, splitLine:{ lineStyle:{ color:'#e5e7eb' } } }, yAxis:{ type:'category', data:['Auditory','Visual','Reading/Writing','Kinesthetic'], axisLine:{ lineStyle:{ color:'#d1d5db' } }, axisLabel:{ color:'#1f2937' } }, series:[{ name:'Learning Style Preference', type:'bar', data: learningStyleData, itemStyle:{ color:function(params){ const colorList=['rgba(141,211,199,1)','rgba(87,181,231,1)','rgba(251,191,114,1)','rgba(252,141,98,1)']; return colorList[params.dataIndex]; }, borderRadius:4 }, label:{ show:true, position:'right', formatter:'{c}%', color:'#1f2937' } }] };
  safeInit('learningStyleChart', learningStyleOption);
  
  
  window.addEventListener('load', () => {
    charts.forEach(c => c.resize());
    setTimeout(() => charts.forEach(c => c.resize()), 50);
  });
  window.addEventListener('resize', () => charts.forEach(c => c.resize()));
});

/* ===============================
   Modal Logic + RAG Fill
================================ */
document.addEventListener('DOMContentLoaded', function () {

  const modal = document.getElementById('assessmentModal');
  const startBtn = document.getElementById('startNewAssessment');
  const cancelBtn = document.getElementById('cancelAssessment');

  const section = document.getElementById('careerPathSection');
//   const careerLink = "https://n8n.srv943390.hstgr.cloud/webhook/2bbf6b68-1fd2-4ece-a78c-5c622a9584d4-psychological";


  // فتح المودال من أي زر فيه أيقونة refresh
  // فتح المودال من أي زرار عليه data-quiz-type (ده زرار Start Assessment لكل كارت)
document.querySelectorAll('button[data-quiz-type]').forEach(btn => {
  btn.addEventListener('click', () => {
    selectedQuizType = btn.dataset.quizType || null;

    if (!modal) return;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  });
});


 if (startBtn) {
  startBtn.addEventListener('click', () => {
    const QUIZ_LINKS = {
      wellbeing: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=wellbeing',
      psychological: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=psychological',
      personality: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=personality',
      career: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Career%20Adaptability',
      riasec: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Career%20Interests%20(RIASEC)',
      ei: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Emotional%20Intelligence%20(EI)',
      work: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Work%20Values',
      cognitive: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=English',
      logical: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Mathematics',
      knowledge: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Knowledge%20Assessment',
      skills: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Skills%20Assessment',
      behaviors: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=Behaviours%20Assessment',
      learning_style: 'https://kentbusinesscollege.org/self_assessment_quiz/?type=learning_style',
    };

    const type = (selectedQuizType || 'wellbeing').toLowerCase();
    window.location.href = QUIZ_LINKS[type] || QUIZ_LINKS.wellbeing;
  });
}

  if (cancelBtn) {
  cancelBtn.addEventListener('click', () => {
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    selectedQuizType = null;
  });
}


  // ===== RAG =====
  function fillScore(key, item) {
    const levelEl = document.getElementById(key + '-level');
    const barEl   = document.getElementById(key + '-bar');

    // لو الداتا مش موجودة: صفّر
    if (!item) {
      if (levelEl) levelEl.textContent = '';
      if (barEl) barEl.style.width = '0%';
      return;
    }

    const lvl  = item.level || '';
    const mean = item.mean;

    const pct = levelToPercent(lvl); // ✅ الحركة حسب level
    const col = levelColor(lvl);

    if (levelEl) {
      levelEl.textContent = `${lvl} (${formatMean(mean)})`; // ✅ يظهر المستوى + القيمة
      levelEl.style.color = col;
    }

    if (barEl) {
      barEl.style.width = pct + '%';
      barEl.style.backgroundColor = col;
    }
  }
  
// Wellbeing Score
  const wellbeingScores = getScores(window.ASSESSMENT_DATA?.wellbeing);

  fillScore('depression', wellbeingScores.depression);
  fillScore('anxiety', wellbeingScores.anxiety);
  fillScore('stress', wellbeingScores.stress);
  fillScore('sleep_quality', wellbeingScores.sleep_quality);
  
  
  // Psychological Score
const psychScores = getScores(window.ASSESSMENT_DATA?.psychological);
fillScore('hope', psychScores?.hope);
fillScore('efficacy', psychScores?.efficacy);
fillScore('psych_resilience', psychScores?.psych_resilience); 
fillScore('optimism', psychScores?.optimism);
fillScore('gratitude', psychScores?.gratitude);

// Personality Traits
const personalityScores = getScores(window.ASSESSMENT_DATA?.personality);
['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
  .forEach(key => fillScore(key, personalityScores?.[key]));

// Career Adaptability
const careerScores = getScores(window.ASSESSMENT_DATA?.career);
fillScore('autonomy', careerScores?.autonomy);
fillScore('adaptability', careerScores?.adaptability);
fillScore('career_resilience', careerScores?.career_resilience); 
fillScore('identity', careerScores?.identity);

// RIASEC
const riasecScores = getScores(window.ASSESSMENT_DATA?.riasec);
['realistic', 'investigative', 'artistic', 'social', 'enterprising', 'conventional']
  .forEach(key => fillScore(key, riasecScores?.[key]));

// Emotional Intelligence
const eiScores = getScores(window.ASSESSMENT_DATA?.ei);
['self_awareness', 'self_management', 'social_awareness', 'relationship_management']
  .forEach(key => fillScore(key, eiScores?.[key]));

// Work Values
const workScores = getScores(window.ASSESSMENT_DATA?.work);
['achievement', 'independence', 'recognition', 'relationships', 'support', 'working_conditions']
  .forEach(key => fillScore(key, workScores?.[key]));

// Cognitive
const cognitiveScores = getScores(window.ASSESSMENT_DATA?.cognitive);
['sentence_correction', 'critical_reasoning', 'reading_comprehension', 'verbal_intelligence', 'memory_cognitive_speed']
  .forEach(key => fillScore(key, cognitiveScores?.[key]));

// Logical
const logicalScores = getScores(window.ASSESSMENT_DATA?.logical);
['arithmetic', 'algebra', 'geometry', 'data_interpretation', 'numerical_reasoning']
  .forEach(key => fillScore(key, logicalScores?.[key]));

// Knowledge
const knowledgeScores = getScores(window.ASSESSMENT_DATA?.knowledge);
['marketing_concepts', 'business_awareness', 'market_research', 'products_channels', 'digital_marketing']
  .forEach(key => fillScore(key, knowledgeScores?.[key]));

// Skills
const skillsScores = getScores(window.ASSESSMENT_DATA?.skills);
['campaign_planning', 'communication', 'project_management', 'data_analysis', 'marketing_tools']
  .forEach(key => fillScore(key, skillsScores?.[key]));

// Behaviors
const behaviorsScores = getScores(window.ASSESSMENT_DATA?.behaviors);
['agility_adaptability', 'creativity_innovation', 'collaboration_teamwork']
  .forEach(key => fillScore(key, behaviorsScores?.[key]));
  
/* ===============================
   Learning Style – Details Render
================================ */
(function renderLearningStyleDetails() {
  const container = document.getElementById('learningStyleResult');
  if (!container) return;

  const block = window.ASSESSMENT_DATA?.learning_style;

  // ⛔ لو مفيش امتحان معمول
  if (!block || !block.learning_styles) {
    container.classList.add('hidden');
    return;
  }

  const dominant = block.dominant_style || '';
  const summary  = block.summary || '';
  const tips     = Array.isArray(block.recommended_approaches)
    ? block.recommended_approaches
    : [];

  // لو مفيش أي نتيجة حقيقية
  if (!dominant && !summary && !tips.length) {
    container.classList.add('hidden');
    return;
  }

  // ✅ اظهر البلوك
  container.classList.remove('hidden');

  // ===== Dominant Style =====
  const dominantEl = document.getElementById('learningStyleDominant');
  if (dominantEl) {
    dominantEl.textContent = dominant || '—';
  }

  // ===== Summary =====
  const summaryEl = document.getElementById('learningStyleDescription');
  if (summaryEl) {
    summaryEl.textContent = summary;
  }

  // ===== Recommendations =====
  const tipsEl = document.getElementById('learningStyleTips');
  if (tipsEl) {
    tipsEl.innerHTML = '';

    tips.forEach(tip => {
      const li = document.createElement('li');
      li.className = 'flex items-start';
      li.innerHTML = `
        <i class="ri-check-line text-primary mr-2 mt-1"></i>
        <span>${tip}</span>
      `;
      tipsEl.appendChild(li);
    });
  }
})();
});

(function(){
  const progressFill = document.getElementById('progressFill');
  if (!progressFill) return;

  function ensureRagObserver(target) {
    try {
      if (target.__ragObserver) return;
      const observer = new MutationObserver(() => {
        const desired = target.dataset.ragColor || "";
        if (desired && target.style.backgroundColor !== desired) {
          target.style.backgroundColor = desired;
        }
        const desiredClass = target.dataset.rag || null;
        if (desiredClass && !target.classList.contains(desiredClass)) {
          target.classList.add(desiredClass);
        }
      });
      observer.observe(target, { attributes: true, attributeFilter: ['style', 'class'] });
      target.__ragObserver = observer;
    } catch (e) {
      // best-effort
    }
  }

  function applyRag(pct) {
    if (!progressFill) return;
    progressFill.classList.remove('rag-red', 'rag-yellow', 'rag-green');
    progressFill.style.backgroundColor = "";

    let rag = null;
    if (pct <= 40) rag = 'rag-red';
    else if (pct <= 70) rag = 'rag-yellow';
    else rag = 'rag-green';

    if (rag) {
      progressFill.classList.add(rag);
      try {
        const root = getComputedStyle(document.documentElement);
        const map = { 'rag-red': '--rag-red', 'rag-yellow': '--rag-yellow', 'rag-green': '--rag-green' };
        const cssVar = map[rag];
        const color = root.getPropertyValue(cssVar).trim() || (rag === 'rag-red' ? '#ef4444' : rag === 'rag-yellow' ? '#f59e0b' : '#16a34a');
        if (color) progressFill.style.backgroundColor = color;
        progressFill.dataset.ragColor = color;
        progressFill.dataset.rag = rag;
        ensureRagObserver(progressFill);
        setTimeout(() => {
          try {
            if (progressFill && progressFill.style.backgroundColor !== color) progressFill.style.backgroundColor = color;
            if (progressFill && !progressFill.classList.contains(rag)) progressFill.classList.add(rag);
          } catch (e) {}
        }, 200);
      } catch (e) {
        // ignore
      }
    }
  }
  
//   For tooltip
(function () {
  let tooltip = null;

  function getTooltip() {
    if (!tooltip) {
      tooltip = document.getElementById('globalTooltip');
    }
    return tooltip;
  }

  document.addEventListener('mousemove', function (e) {
    const wrapper = e.target.closest('.tooltip-wrapper');
    const tip = getTooltip();

    if (!wrapper || !tip) {
      if (tip) tip.classList.remove('show');
      return;
    }

    const text = wrapper.getAttribute('data-tooltip');
    if (!text) return;

    tip.textContent = text;
    tip.classList.add('show');

    const rect = wrapper.getBoundingClientRect();

    // حساب العرض
    tip.style.visibility = 'hidden';
    tip.style.left = '0px';
    tip.style.top = '0px';

    const w = tip.offsetWidth;
    const padding = 12;
    const vw = window.innerWidth;

    let left = rect.left + rect.width / 2 - w / 2;
    if (left < padding) left = padding;
    if (left + w > vw - padding) left = vw - w - padding;

    tip.style.left = left + 'px';
    tip.style.top = rect.top - 10 + 'px';
    tip.style.transform = 'translateY(-100%)';
    tip.style.visibility = 'visible';
  });

  document.addEventListener('mouseleave', () => {
    if (tooltip) tooltip.classList.remove('show');
  });
})();



  // Expose a simple API to call from your code or console
  window.applyRagToProgressFill = function(pct) { applyRag(pct); };
})();
