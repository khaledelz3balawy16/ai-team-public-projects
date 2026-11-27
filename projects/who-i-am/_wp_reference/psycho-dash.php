<?php
/*
Plugin Name: Psycological Dashboard
Description: User Psychological Assessment Dashboard
Version: 1.0
Author: Kent Dashboard
*/

if (!defined('ABSPATH')) exit;

add_action('wp_enqueue_scripts', function () {

    if (!is_singular()) return;

    global $post;
    if (!$post || !has_shortcode($post->post_content, 'psychological-dashboard')) return;

    if (!is_user_logged_in()) return;

    $css_path = plugin_dir_path(__FILE__) . 'assets/css/psycho-dash.css';
    $js_path  = plugin_dir_path(__FILE__) . 'assets/js/psycho-dash.js';

    // ✅ Tailwind (بيحل 90% من مشاكل الشكل + modal)
    wp_enqueue_style(
        'tailwind',
        'https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css',
        [],
        '2.2.19'
    );

    // ✅ Remix Icon (عشان ri- icons اللي في الـ markup)
    wp_enqueue_style(
        'remixicon',
        'https://cdn.jsdelivr.net/npm/remixicon@4.6.0/fonts/remixicon.css',
        [],
        '4.6.0'
    );

    // (اختياري) FontAwesome لأن عندك fa-solid في جزء الكارير
    wp_enqueue_style(
        'fontawesome',
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
        [],
        '6.5.0'
    );

    // ✅ CSS بتاعك بعد Tailwind عشان يعمل override
    wp_enqueue_style(
        'psycho-dash-css',
        plugin_dir_url(__FILE__) . 'assets/css/psycho-dash.css',
        ['tailwind'],
        file_exists($css_path) ? filemtime($css_path) : '1.0'
    );

    wp_enqueue_script(
        'echarts',
        'https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js',
        [],
        null,
        true
    );

    wp_enqueue_script(
        'psycho-dash-js',
        plugin_dir_url(__FILE__) . 'assets/js/psycho-dash.js',
        ['echarts'],
        file_exists($js_path) ? filemtime($js_path) : '1.0',
        true
    );

    $user = wp_get_current_user();
    $programme = get_user_meta($user->ID, 'programme', true);

    wp_localize_script('psycho-dash-js', 'PSYCHO', [
        'restUrl' => esc_url_raw(rest_url()),
        'nonce'   => wp_create_nonce('wp_rest'),
        'user'    => [
            'login'     => $user->user_login,
            'name'      => $user->display_name,
            'email'     => $user->user_email,
            'programme' => $programme ?: '',
        ],
    ]);
});




add_action('rest_api_init', function () {
  register_rest_route('psycho/v1', '/career-path/shown', [
    'methods'  => 'POST',
    'permission_callback' => function () {
      return is_user_logged_in();
    },
    'callback' => function () {
    $user = wp_get_current_user();

    // ✅ استثناء rawan: متسجليش timestamp
    if ($user && $user->user_login === 'rawan') {
        return new WP_REST_Response([
            'ok' => true,
            'skipped' => true
        ], 200);
    }

    // باقي المستخدمين
    $uid = get_current_user_id();
    update_user_meta($uid, 'career_path_last_shown', current_time('timestamp'));

    return new WP_REST_Response(['ok' => true], 200);
}

  ]);
});


add_shortcode('psychological-dashboard', function () {

    if (!is_user_logged_in()) {
        return '<p>Please login first.</p>';
    }

    global $wpdb;
    $user = wp_get_current_user();

    $table = $wpdb->prefix . 'assessment_scores';

    $row = $wpdb->get_row(
    $wpdb->prepare(
        "SELECT * FROM $table WHERE email = %s",
        $user->user_email
    ),
    ARRAY_A
);

// ✅ لو مفيش بيانات، خليه Array فاضي وكمل عادي
if (!is_array($row)) {
    $row = [];
}


    function safe_col($row, $key) {
        return isset($row[$key]) ? $row[$key] : null;
    }

    // ✅ بدل wrap_scores: نفك الـ JSON زي ما هو بدون تغليف إضافي
    function decode_assessment_json($json) {
        if (!$json) return [];
        $decoded = json_decode($json, true);
        if (!is_array($decoded)) return [];
        return $decoded;
    }

    // ✅ هنا بقى كل بلوك هيبقى شكله:
    // wellbeing => [ "scores" => {...}, "overall_wellbeing" => {...} ]
    $ASSESSMENT_DATA = [
        'wellbeing'     => decode_assessment_json(safe_col($row,'wellbeing_score')),
        'psychological' => decode_assessment_json(safe_col($row,'Psychological_score')),
        'personality'   => decode_assessment_json(safe_col($row,'Personality_score')),
        'career'        => decode_assessment_json(safe_col($row,'Career_score')),
        'riasec'        => decode_assessment_json(safe_col($row,'RIASEC_score')),
        'ei'            => decode_assessment_json(safe_col($row,'EI_score')),
        'work'          => decode_assessment_json(safe_col($row,'Work_score')),
        'cognitive'     => decode_assessment_json(safe_col($row,'CognitiveSkills_score')),
        'logical'       => decode_assessment_json(safe_col($row,'LogicalSkills_score')),
        'knowledge'     => decode_assessment_json(safe_col($row,'Knowledge_score')),
        'skills'        => decode_assessment_json(safe_col($row,'Skills_score')),
        'behaviors'     => decode_assessment_json(safe_col($row,'Behaviors_score')),
        'learning_style' => decode_assessment_json(safe_col($row,'learning_style_score')),
    ];
    
    $quiz_base_url = site_url('/self_assessment_quiz/');
    
    // return to Dashboard
    $user = wp_get_current_user();

    $dashboard_url = site_url('/student-dashboard/');

    if (in_array('administrator', $user->roles)) {
    $dashboard_url = site_url('/admin-dashboard/');
    }  
    
    ob_start();
    ?>

   <script>
    window.ASSESSMENT_DATA = <?php echo wp_json_encode($ASSESSMENT_DATA); ?>;
    window.QUIZ_BASE_URL   = <?php echo wp_json_encode($quiz_base_url); ?>;
</script>

<div id="psycho-dashboard">
  <!-- Page Header -->
<section class="bg-primary text-white py-8">
<div class="container mx-auto px-4">
<div class="flex flex-col md:flex-row items-center justify-between">
<div>
<h1 class="text-3xl font-bold mb-2">Who I Am</h1>
<p class="text-lg opacity-90">Discover your personality profile, learning style, and strengths</p>
</div>
<div class="mt-4 md:mt-0 flex items-center gap-3">
<a href="<?php echo esc_url($dashboard_url); ?>"
   class="px-4 py-2 bg-white text-primary font-medium !rounded-button whitespace-nowrap hover:bg-gray-100 transition flex items-center" style="border-radius:50px;">
  <i class="ri-arrow-left-line mr-2"></i>
  Back to Your Dashboard
</a>

<!--<button class="px-4 py-2 bg-white text-primary font-medium !rounded-button whitespace-nowrap hover:bg-gray-100 transition flex items-center">-->
<!--<i class="ri-download-line mr-2"></i> Download Report-->
<!--</button>-->
</div>
</div>
</div>
</section>
<!-- Main Dashboard -->
<section class="py-8">
<div class="container mx-auto px-4">
<!-- Dashboard Navigation -->
<div class="mb-8 bg-white rounded-lg shadow-sm p-4">
<div class="flex flex-wrap gap-4">
<div class="flex-1">
<div class="flex items-center gap-4">
<!--<div class="w-16 h-16 rounded-full overflow-hidden">-->
<!--<img src="https://readdy.ai/api/search-image?query=professional%252520headshot%252520of%252520a%252520young%252520student%252520with%252520neutral%252520background%25252C%252520high%252520quality%252520portrait&width=200&height=200&seq=profile2&orientation=squarish" alt="Student Profile" class="w-full h-full object-cover">-->
<!--</div>-->
<div>
<h2 class="text-xl font-semibold text-gray-900">
  <?php echo esc_html($user->display_name); ?>
</h2>
<p class="text-primary font-medium text-sm">
  <?php echo esc_html($user->user_email); ?>
</p>

</div>
</div>
</div>
<!--<div class="flex-1 flex items-center justify-end gap-6">-->
<!--<div class="text-center">-->
<!--<div class="text-3xl font-bold text-primary">1,250</div>-->
<!--<div class="text-sm text-gray-600">Reward Points</div>-->
<!--</div>-->
<!--<div class="text-center">-->
<!--<div class="text-3xl font-bold text-primary">#12</div>-->
<!--<div class="text-sm text-gray-600">Leaderboard Rank</div>-->
<!--</div>-->
<!--</div>-->
</div>
</div>
<!-- Dashboard Tabs -->
<div class="mb-6 bg-white rounded-lg shadow-sm p-4">
<div class="flex flex-wrap gap-3">
<button class="tab-button active px-5 py-2.5 !rounded-full text-sm font-medium whitespace-nowrap" onclick="document.getElementById('mentalWellbeingSection').scrollIntoView({behavior: 'smooth'})">Mental Well-Being</button>
<button class="tab-button px-5 py-2.5 !rounded-full text-sm font-medium bg-gray-100 text-gray-700 whitespace-nowrap" onclick="document.getElementById('PsychologicalCapital').scrollIntoView({behavior: 'smooth'})">Psychometric & Aptitude</button>
<button class="tab-button px-5 py-2.5 !rounded-full text-sm font-medium bg-gray-100 text-gray-700 whitespace-nowrap" onclick="document.getElementById('ksbs').scrollIntoView({behavior: 'smooth'})">Knowledge, Skills & Behaviors</button>
</div>
</div>
<!-- Mental Well-Being Section -->
<div id="mentalWellbeingSection" class="mb-8">
<div class="grid md:grid-cols-1 gap-6">
<!-- Wellbeing Assessment -->
<div class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Wellbeing Assessment</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 15, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">Your wellbeing scores indicate moderate stress levels balanced by good sleep quality. Consider stress management techniques to improve your overall wellbeing.</p>
</div>
<div class="md:w-2/5">
<div id="wellbeingChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div>
    <div class="flex justify-between text-sm">
      <span class="text-gray-600">Depression</span>
      <span id="depression-level" class="font-medium text-primary"></span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2">
      <div id="depression-bar" class="bg-primary h-2 rounded-full" style="width:0%"></div>
    </div>
  </div>

  <!-- Anxiety -->
  <div>
    <div class="flex justify-between text-sm">
      <span class="text-gray-600">Anxiety</span>
      <span id="anxiety-level" class="font-medium text-primary"></span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2">
      <div id="anxiety-bar" class="bg-primary h-2 rounded-full" style="width:0%"></div>
    </div>
  </div>

  <!-- Stress -->
  <div>
    <div class="flex justify-between text-sm">
      <span class="text-gray-600">Stress</span>
      <span id="stress-level" class="font-medium text-primary"></span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2">
      <div id="stress-bar" class="bg-primary h-2 rounded-full" style="width:0%"></div>
    </div>
  </div>

  <!-- Sleep Quality -->
  <div>
    <div class="flex justify-between text-sm">
      <span class="text-gray-600">Sleep Quality</span>
      <span id="sleep_quality-level" class="font-medium text-primary"></span>
    </div>
    <div class="w-full bg-gray-200 rounded-full h-2">
      <div id="sleep_quality-bar" class="bg-primary h-2 rounded-full" style="width:0%"></div>
    </div>
  </div>

</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="wellbeing" class="px-4 py-2 bg-primary text-white font-medium !rounded-button ...">
  <i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- Psychological Capital -->
<div id="PsychologicalCapital" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Psychological Capital</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 15, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">You show strong resilience and optimism, which are valuable traits for academic success. Your hope and efficacy scores indicate room for growth in goal-setting and self-belief.</p>
</div>
<div class="md:w-2/5">
<div id="psychCapitalChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Hope</span>
<span id="hope-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="hope-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Efficancy</span>
<span id="efficacy-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="efficacy-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Resilience</span>
<span id="psych_resilience-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="psych_resilience-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Optimism</span>
<span id="optimism-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="optimism-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Gratitude</span>
<span id="gratitude-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="gratitude-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="psychological" class="px-4 py-2 bg-primary text-white font-medium !rounded-button ...">
  <i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- Personality Traits -->
<div id="personalitySection" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Personality Traits</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 10, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">Your personality profile shows high openness to new experiences and conscientiousness, making you well-suited for creative yet structured work. Your moderate extraversion balances teamwork with independent tasks.</p>
</div>
<div class="md:w-2/5">
<div id="personalityChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Openness</span>
<span id="openness-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="openness-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Conscientiousness</span>
<span id="conscientiousness-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="conscientiousness-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Extraversion</span>
<span id="extraversion-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="extraversion-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Agreeableness</span>
<span id="agreeableness-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="agreeableness-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Neuroticism</span>
<span id="neuroticism-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="neuroticism-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="personality" class="px-4 py-2 bg-primary text-white font-medium !rounded-button ...">
  <i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- Career Adaptability -->
<div id="careerSection" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Career Adaptability</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 10, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">You demonstrate strong career autonomy and adaptability, showing you're prepared to navigate changing work environments. Your professional identity is developing well, providing a solid foundation for career growth.</p>
</div>
<div class="md:w-2/5">
<div id="careerChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Career Autonomy</span>
<span id="autonomy-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="autonomy-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Adaptability</span>
<span id="adaptability-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="adaptability-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Personal Resilience</span>
<span id="career_resilience-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="career_resilience-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Identity</span>
<span id="identity-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="identity-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="career" class="px-4 py-2 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition">
<i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
</div>
</div>
<!-- Career Interests (RIASEC) -->
<div id="riasecSection" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Career Interests (RIASEC)</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 20, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">Your RIASEC profile shows strong interests in Social and Enterprising activities, suggesting you would excel in roles involving leadership, persuasion, and helping others. Consider careers that combine these elements.</p>
</div>
<div class="md:w-2/5">
<div id="riasecChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Realistic</span>
<span id="realistic-level" class="font-medium"></span>   
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="realistic-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Investigative</span>
<span id="investigative-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="investigative-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Artistic</span>
<span id="artistic-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="artistic-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Social</span>
<span id="social-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="social-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Enterprising</span>
<span id="enterprising-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="enterprising-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Conventional</span>
<span id="conventional-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="conventional-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="riasec" class="px-4 py-2 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition">
<i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- Emotional Intelligence (EI) -->
<div id="eiSection" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Emotional Intelligence (EI)</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 18, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">Your EI profile indicates strong self-awareness and relationship management skills. These strengths will serve you well in leadership roles and team environments. Consider developing social awareness further.</p>
</div>
<div class="md:w-2/5">
<div id="eiChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Self-Awareness</span>
<span id="self_awareness-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="self_awareness-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Self-Management</span>
<span id="self_management-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="self_management-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Social Awareness</span>
<span id="social_awareness-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="social_awareness-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Relationship Management</span>
<span id="relationship_management-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="relationship_management-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button  data-quiz-type="ei" class="px-4 py-2 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition">
<i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- Work Values -->
<div id="workValuesSection" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Work Values</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 15, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">Your work values profile shows a strong emphasis on achievement and independence, with a balanced appreciation for relationships and support. This suggests you would thrive in roles offering autonomy and growth opportunities.</p>
</div>
<div class="md:w-2/5">
<div id="workValuesChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Achievement</span>
<span id="achievement-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="achievement-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Independence</span>
<span id="independence-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="independence-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Recognition</span>
<span id="recognition-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="recognition-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Relationships</span>
<span id="relationships-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="relationships-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Support</span>
<span id="support-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="support-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Working Conditions</span>
<span id="working_conditions-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="working_conditions-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="work" class="px-4 py-2 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition">
<i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- English & Cognitive Skills -->
<div id="ksbs" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">English & Cognitive Skills</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 22, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">Your English and cognitive skills profile shows strong performance in critical reasoning and verbal intelligence. Consider focusing on improving sentence correction and memory speed for comprehensive development.</p>
</div>
<div class="md:w-2/5">
<div id="englishCognitiveChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Sentence Correction</span>
<span id="sentence_correction-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="sentence_correction-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Critical Reasoning</span>
<span id="critical_reasoning-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="critical_reasoning-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Reading Comprehension</span>
<span id="reading_comprehension-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="reading_comprehension-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Verbal Intelligence</span>
<span id="verbal_intelligence-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="verbal_intelligence-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Memory & Cognitive Speed</span>
<span id="memory_cognitive_speed-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="memory_cognitive_speed-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="cognitive" class="px-4 py-2 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition">
<i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- Mathematics & Logical Skills -->
<div id="mathLogicalSection" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Mathematics & Logical Skills</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 22, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">Your mathematical and logical reasoning abilities are well-balanced, with particular strengths in data interpretation and numerical reasoning. Consider additional practice in geometry and spatial reasoning.</p>
</div>
<div class="md:w-2/5">
<div id="mathLogicalChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Arithmetic</span>
<span id="arithmetic-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="arithmetic-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Algebra</span>
<span id="algebra-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="algebra-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Geometry</span>
<span id="geometry-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="geometry-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Data Interpretation</span>
<span id="data_interpretation-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="data_interpretation-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Numerical Reasoning</span>
<span id="numerical_reasoning-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="numerical_reasoning-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="logical" class="px-4 py-2 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition">
<i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- Knowledge, Skills & Behaviors Section -->
<div class="grid md:grid-cols-1 gap-6 mb-8">
<!-- Knowledge Radar -->
<div id="knowledgeSection" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Knowledge Assessment</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 25, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">Your knowledge profile shows strong understanding of digital marketing and market research. Consider focusing on developing deeper business awareness and product knowledge.</p>
</div>
<div class="md:w-2/5">
<div id="knowledgeChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Marketing Concepts</span>
<span id="marketing_concepts-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="marketing_concepts-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Business Awareness</span>
<span id="business_awareness-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="business_awareness-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Market Research</span>
<span id="market_research-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="market_research-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Products & Channels</span>
<span id="products_channels-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="products_channels-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Digital Marketing</span>
<span id="digital_marketing-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="digital_marketing-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="knowledge" class="px-4 py-2 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition">
<i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- Skills Radar -->
<div id="skillsSection" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Skills Assessment</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 25, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">Your skills profile demonstrates excellence in communication and campaign planning. Project management skills show room for growth and development.</p>
</div>
<div class="md:w-2/5">
<div id="skillsChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Campaign Planning</span>
<span id="campaign_planning-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="campaign_planning-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Communication</span>
<span id="communication-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="communication-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Project Management</span>
<span id="project_management-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="project_management-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Data Analysis</span>
<span id="data_analysis-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="data_analysis-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Marketing Tools</span>
<span id="marketing_tools-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="marketing_tools-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="skills" class="px-4 py-2 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition">
<i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- Behaviors Radar -->
<div id="behaviorsSection" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<div class="flex justify-between items-center">
<h3 class="text-lg font-semibold text-gray-900">Behaviors Assessment</h3>
<!--<div class="text-sm text-gray-500">Last updated: June 25, 2025</div>-->
</div>
</div>
<div class="p-5">
<div class="flex flex-col md:flex-row">
<div class="md:w-1/3 mb-4 md:mb-0">
<h4 class="font-medium text-gray-900 mb-2">Interpretation</h4>
<p class="text-sm text-gray-600">Your behavioral profile shows exceptional creativity and innovation, with strong teamwork abilities. Your adaptability in various situations is a notable strength.</p>
</div>
<div class="md:w-2/5">
<div id="behaviorsChart" class="radar-chart"></div>
</div>
<div class="md:w-1/4 pl-0 md:pl-4">
<h4 class="font-medium text-gray-900 mb-2">Scores</h4>
<div class="space-y-3">
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Agility & Adaptability</span>
<span id="agility_adaptability-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="agility_adaptability-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Creativity & Innovation</span>
<span id="creativity_innovation-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="creativity_innovation-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
<div>
<div class="flex justify-between text-sm">
<span class="text-gray-600">Collaboration & Teamwork</span>
<span id="collaboration_teamwork-level" class="font-medium"></span>
</div>
<div class="w-full bg-gray-200 rounded-full h-2">
<div id="collaboration_teamwork-bar" class="h-2 rounded-full" style="width:0%"></div>
</div>
</div>
</div>
</div>
</div>
<div class="mt-6 pt-4 border-t border-gray-100">
<div class="flex justify-between items-center">
<div class="flex items-center gap-2">
<!--<span class="inline-block w-3 h-3 bg-[#74b9df] rounded-full"></span>-->
<!--<span class="text-sm text-gray-600">Current Month</span>-->
<!--<span class="inline-block w-3 h-3 bg-gray-300 rounded-full ml-3"></span>-->
<!--<span class="text-sm text-gray-600">Previous Month</span>-->
</div>
<button data-quiz-type="behaviors" class="px-4 py-2 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition">
<i class="ri-refresh-line mr-1"></i> Start Assessment
</button>
</div>
</div>
</div>
</div>
<!-- Learning Style & Career Recommendations -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8 items-start">
<!-- Learning Style Preferences -->
<div id="learningStyleSection" class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden h-full flex flex-col">
<div class="p-5 border-b border-gray-100">
<h3 class="text-lg font-semibold text-gray-900">Learning Style Preferences</h3>
</div>
<div class="p-5">
<div id="learningStyleChart" class="h-64 w-full mb-4"></div>
<div id="learningStyleResult" class="space-y-4 hidden">
  <div>
    <h4 class="font-medium text-gray-900 mb-2">
      Your Dominant Learning Style:
      <span id="learningStyleDominant" class="text-primary"></span>
    </h4>
    <p id="learningStyleDescription" class="text-sm text-gray-600"></p>
  </div>

  <div>
    <h4 class="font-medium text-gray-900 mb-2">Recommended Learning Approaches:</h4>
    <ul id="learningStyleTips" class="space-y-2 text-sm text-gray-600"></ul>
  </div>
</div>
<div class="mt-6 pt-6 border-t border-gray-100">
  <button
    data-quiz-type="learning_style"
    class="w-full px-4 py-3 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition flex items-center justify-center">
    <i class="ri-file-list-3-line mr-2"></i>
    Take Learning Style Assessment
  </button>
</div>
</div>
</div>
<?php
// ====== Gating data (PHP) ======
$completed = 0;
foreach ([
  'wellbeing','psychological','personality','career','riasec','ei','work',
  'cognitive','logical','knowledge','skills','behaviors'
] as $k) {
  $blk = $ASSESSMENT_DATA[$k] ?? [];
  if (is_array($blk) && !empty($blk)) $completed++;
}

$min_required = 6;

$current_user = wp_get_current_user();
$is_rawan = ($current_user && strtolower($current_user->user_login) === 'rawan');

$last_shown = get_user_meta(get_current_user_id(), 'career_path_last_shown', true);
$last_ts = $last_shown ? (int) $last_shown : 0;

$now = current_time('timestamp');

// Daily use for (show my career path) button 
$already_this_month = ($last_ts > 0) && (date('Y-m-d', $last_ts) === date('Y-m-d', $now));

if ($is_rawan) {
    $can_show = true;
    $should_show_section = true;
} else {
    $can_show = ($completed >= $min_required) && !$already_this_month;
    $should_show_section = $already_this_month;
}
?>

 <!--Career Path Recommendations (Gated) -->
  <div class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden h-full flex flex-col">
  <div class="p-5 border-b border-gray-100 flex items-center justify-between">
    <h3 class="text-lg font-semibold text-gray-900">Career Path Recommendations</h3>

    <div class="career-tooltip-wrapper">
  <button
    id="showCareerPathBtn"
    disabled
    class="px-4 py-2 bg-primary text-white font-medium rounded-button
           disabled:opacity-50 disabled:cursor-not-allowed"
  >
    Show my career path
  </button>

  <div class="career-tooltip">
    Generate personalised career recommendations based on your completed assessments
  </div>
</div>

  </div>

  <!-- هنا بنخفي/نظهر البلوك -->
  <div id="careerPathSection" class="hidden">
    <div class="p-5">
      <p id="careerStatusText" class="text-sm text-gray-600 mb-4">
      Click the button to generate your career path recommendations.
    </p>

      <div
        id="careerCards"
        class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
      </div>

      <div id="careerSkillsWrapper" class="hidden">
  <h4 class="font-medium text-gray-900 mb-2">Skills to Develop:</h4>
  <ul id="careerSkills" class="space-y-2 text-sm text-gray-600"></ul>
</div>
</div>
</div>

<script>
  window.CAREER_GATE = {
    completed: <?php echo (int)$completed; ?>,
    minRequired: <?php echo (int)$min_required; ?>,
    canShow: <?php echo $can_show ? 'true' : 'false'; ?>,
    alreadyThisMonth: <?php echo $already_this_month ? 'true' : 'false'; ?>
  };
</script>
</div>
</div>
 
<!-- Assessment History & Actions -->
 <!--<div class="grid md:grid-cols-3 gap-6 mb-8"> -->
<!-- Assessment History -->
<!-- <div class="md:col-span-2 dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<h3 class="text-lg font-semibold text-gray-900">Assessment History</h3>
</div>
<div class="p-5">
<div class="overflow-x-auto">
<table class="min-w-full divide-y divide-gray-200">
<thead>
<tr>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assessment Type</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date Completed</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score/Result</th>
<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Change</th>
</tr>
</thead>
<tbody class="bg-white divide-y divide-gray-200">
<tr>
<td class="px-4 py-3 whitespace-nowrap">
<div class="flex items-center">
<div class="w-8 h-8 flex items-center justify-center bg-primary/10 rounded-full mr-3">
<i class="ri-mental-health-line text-primary"></i>
</div>
<div class="text-sm font-medium text-gray-900">Wellbeing Assessment</div>
</div>
</td>
<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">June 15, 2025</td>
<td class="px-4 py-3 whitespace-nowrap">
<span class="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">Balanced</span>
</td>
<td class="px-4 py-3 whitespace-nowrap text-sm text-green-600">
<div class="flex items-center">
<i class="ri-arrow-up-line mr-1"></i>
<span>+5%</span>
</div>
</td>
</tr>
<tr>
<td class="px-4 py-3 whitespace-nowrap">
<div class="flex items-center">
<div class="w-8 h-8 flex items-center justify-center bg-primary/10 rounded-full mr-3">
<i class="ri-user-heart-line text-primary"></i>
</div>
<div class="text-sm font-medium text-gray-900">Psychological Capital</div>
</div>
</td>
<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">June 15, 2025</td>
<td class="px-4 py-3 whitespace-nowrap">
<span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">Strong</span>
</td>
<td class="px-4 py-3 whitespace-nowrap text-sm text-green-600">
<div class="flex items-center">
<i class="ri-arrow-up-line mr-1"></i>
<span>+8%</span>
</div>
</td>
</tr>
<tr>
<td class="px-4 py-3 whitespace-nowrap">
<div class="flex items-center">
<div class="w-8 h-8 flex items-center justify-center bg-primary/10 rounded-full mr-3">
<i class="ri-user-search-line text-primary"></i>
</div>
<div class="text-sm font-medium text-gray-900">Personality Assessment</div>
</div>
</td>
<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">June 10, 2025</td>
<td class="px-4 py-3 whitespace-nowrap">
<span class="px-2 py-1 text-xs font-medium bg-purple-100 text-purple-800 rounded-full">ENFJ-T</span>
</td>
<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
<span>No change</span>
</td>
</tr>
<tr>
<td class="px-4 py-3 whitespace-nowrap">
<div class="flex items-center">
<div class="w-8 h-8 flex items-center justify-center bg-primary/10 rounded-full mr-3">
<i class="ri-briefcase-line text-primary"></i>
</div>
<div class="text-sm font-medium text-gray-900">Career Adaptability</div>
</div>
</td>
<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">June 10, 2025</td>
<td class="px-4 py-3 whitespace-nowrap">
<span class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">High</span>
</td>
<td class="px-4 py-3 whitespace-nowrap text-sm text-green-600">
<div class="flex items-center">
<i class="ri-arrow-up-line mr-1"></i>
<span>+3%</span>
</div>
</td>
</tr>
<tr>
<td class="px-4 py-3 whitespace-nowrap">
<div class="flex items-center">
<div class="w-8 h-8 flex items-center justify-center bg-primary/10 rounded-full mr-3">
<i class="ri-book-open-line text-primary"></i>
</div>
<div class="text-sm font-medium text-gray-900">Learning Style</div>
</div>
</td>
<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">May 25, 2025</td>
<td class="px-4 py-3 whitespace-nowrap">
<span class="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">Visual-Kinesthetic</span>
</td>
<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
<span>No change</span>
</td>
</tr>
</tbody>
</table>
</div>
</div>
</div> -->
<!-- Quick Actions -->
<!-- <div class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden">
<div class="p-5 border-b border-gray-100">
<h3 class="text-lg font-semibold text-gray-900">Quick Actions</h3>
</div>
<div class="p-5">
<div class="space-y-4">
<button class="w-full px-4 py-3 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition flex items-center justify-center">
<i class="ri-refresh-line mr-2"></i>
Retake All Assessments
</button>
<button class="w-full px-4 py-3 bg-white border border-primary text-primary font-medium !rounded-button whitespace-nowrap hover:bg-gray-50 transition flex items-center justify-center">
<i class="ri-download-line mr-2"></i>
Download Detailed Report
</button>
<button class="w-full px-4 py-3 bg-white border border-gray-200 text-gray-700 font-medium !rounded-button whitespace-nowrap hover:bg-gray-50 transition flex items-center justify-center">
<i class="ri-user-star-line mr-2"></i>
Schedule Coaching Session
</button>
<button class="w-full px-4 py-3 bg-white border border-gray-200 text-gray-700 font-medium !rounded-button whitespace-nowrap hover:bg-gray-50 transition flex items-center justify-center">
<i class="ri-share-line mr-2"></i>
Share Results with Mentor
</button>
</div>
<div class="mt-6 pt-6 border-t border-gray-100">
<h4 class="font-medium text-gray-900 mb-3">Notification Preferences</h4>
<div class="space-y-3">
<div class="flex items-center justify-between">
<span class="text-sm text-gray-600">Monthly assessment reminders</span>
<label class="custom-switch">
<input type="checkbox" checked>
<span class="switch-slider"></span>
</label>
</div>
<div class="flex items-center justify-between">
<span class="text-sm text-gray-600">Progress reports</span>
<label class="custom-switch">
<input type="checkbox" checked>
<span class="switch-slider"></span>
</label>
</div>
<div class="flex items-center justify-between">
<span class="text-sm text-gray-600">Coaching recommendations</span>
<label class="custom-switch">
<input type="checkbox">
<span class="switch-slider"></span>
</label>
</div>
<div class="flex items-center justify-between">
<span class="text-sm text-gray-600">Career opportunity alerts</span>
<label class="custom-switch">
<input type="checkbox" checked>
<span class="switch-slider"></span>
</label>
</div>
</div>
</div>
</div>
</div>
</div> -->
<!-- Personalized Recommendations -->
<!-- <div class="dashboard-card bg-white rounded-lg shadow-sm overflow-hidden mb-8">
<div class="p-5 border-b border-gray-100">
<h3 class="text-lg font-semibold text-gray-900">Personalized Recommendations</h3>
</div>
<div class="p-5">
<div class="grid md:grid-cols-3 gap-6">
<div class="border border-gray-200 rounded-lg p-4 hover:border-primary transition-colors">
<div class="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
<i class="ri-book-read-line text-primary ri-lg"></i>
</div>
<h4 class="font-medium text-gray-900 mb-2">Learning Resources</h4>
<p class="text-sm text-gray-600 mb-3">Based on your visual-kinesthetic learning style, these resources will enhance your learning experience:</p>
<ul class="space-y-2 text-sm text-gray-600">
<li class="flex items-start">
<i class="ri-check-line text-primary mr-2 mt-1"></i>
<span>Interactive Marketing Strategy Simulator</span>
</li>
<li class="flex items-start">
<i class="ri-check-line text-primary mr-2 mt-1"></i>
<span>Visual Guide to Brand Management</span>
</li>
<li class="flex items-start">
<i class="ri-check-line text-primary mr-2 mt-1"></i>
<span>Hands-on Market Research Workshop</span>
</li>
</ul>
<a href="#" class="mt-4 inline-flex items-center text-primary text-sm font-medium hover:underline">
View all resources
<i class="ri-arrow-right-line ml-1"></i>
</a>
</div>
<div class="border border-gray-200 rounded-lg p-4 hover:border-primary transition-colors">
<div class="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
<i class="ri-group-line text-primary ri-lg"></i>
</div>
<h4 class="font-medium text-gray-900 mb-2">Study Groups & Peers</h4>
<p class="text-sm text-gray-600 mb-3">Connect with peers who complement your learning style and personality traits:</p>
<ul class="space-y-2 text-sm text-gray-600">
<li class="flex items-start">
<i class="ri-check-line text-primary mr-2 mt-1"></i>
<span>Marketing Innovation Study Group (Tuesdays)</span>
</li>
<li class="flex items-start">
<i class="ri-check-line text-primary mr-2 mt-1"></i>
<span>Visual Learners Community</span>
</li>
<li class="flex items-start">
<i class="ri-check-line text-primary mr-2 mt-1"></i>
<span>Project Management Peer Mentoring</span>
</li>
</ul>
<a href="#" class="mt-4 inline-flex items-center text-primary text-sm font-medium hover:underline">
Join a group
<i class="ri-arrow-right-line ml-1"></i>
</a>
</div>
<div class="border border-gray-200 rounded-lg p-4 hover:border-primary transition-colors">
<div class="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
<i class="ri-mental-health-line text-primary ri-lg"></i>
</div>
<h4 class="font-medium text-gray-900 mb-2">Wellbeing Activities</h4>
<p class="text-sm text-gray-600 mb-3">Enhance your mental wellbeing with these activities that align with your personality profile:</p>
<ul class="space-y-2 text-sm text-gray-600">
<li class="flex items-start">
<i class="ri-check-line text-primary mr-2 mt-1"></i>
<span>Guided Mindfulness for Stress Management</span>
</li>
<li class="flex items-start">
<i class="ri-check-line text-primary mr-2 mt-1"></i>
<span>Creative Problem-Solving Workshops</span>
</li>
<li class="flex items-start">
<i class="ri-check-line text-primary mr-2 mt-1"></i>
<span>Outdoor Team Building Activities</span>
</li>
</ul>
<a href="#" class="mt-4 inline-flex items-center text-primary text-sm font-medium hover:underline">
Explore activities
<i class="ri-arrow-right-line ml-1"></i>
</a>
</div>
</div>
</div>
</div>
</div>
</section> -->


<!-- Modal Dialog -->
<div id="assessmentModal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
  <div class="bg-white rounded-lg max-w-md w-full mx-4 overflow-hidden shadow-xl">
    <div class="p-6">
      <h3 class="text-xl font-semibold text-gray-900 mb-4">Retake Assessment?</h3>
      <p class="text-gray-600 mb-6">This assessment takes approximately 10-15 minutes to complete.</p>
      <div class="flex flex-col gap-3">
        <button
  id="startNewAssessment"
  class="w-full px-4 py-2 bg-primary text-white font-medium !rounded-button whitespace-nowrap hover:bg-primary/90 transition flex items-center justify-center">
  <i class="ri-play-line mr-2"></i> Start New Assessment
</button>

        <button id="cancelAssessment" class="w-full px-4 py-2 bg-white border border-gray-200 text-gray-700 font-medium !rounded-button whitespace-nowrap hover:bg-gray-50 transition flex items-center justify-center">
          Cancel
        </button>
      </div>
    </div>
  </div>
</div>
<div id="globalTooltip" class="global-tooltip"></div>
</div>

<?php  
    return ob_get_clean();
}); 