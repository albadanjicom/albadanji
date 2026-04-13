/* ===================================================
   MR Newsletter — Frontend Logic
   =================================================== */

// Type → badge CSS class mapping
const TYPE_CLASS_MAP = {
  '좌담회': 'posting-card__type--fgd',
  '설문조사': 'posting-card__type--online',
  '온라인': 'posting-card__type--online',
  '맛테스트': 'posting-card__type--taste',
  '인터뷰': 'posting-card__type--interview',
  '유치조사': 'posting-card__type--other',
  '패널모집': 'posting-card__type--other',
  '기타': 'posting-card__type--other',
  '상시모집': 'posting-card__type--always',
};

// Type → icon mapping
const TYPE_ICON_MAP = {
  '좌담회': '&#128172;',
  '온라인': '&#128187;',
  '설문조사': '&#128187;',
  '맛테스트': '&#127860;',
  '인터뷰': '&#127908;',
  '유치조사': '&#128230;',
  '패널모집': '&#128101;',
  '기타': '&#128196;',
  '상시모집': '&#128260;',
};

let allPostings = [];

// ── Determine effective type (상시모집 if no date or '상시' keyword) ──
function getEffectiveType(p) {
  const title = (p.title || '').toLowerCase();
  const raw = (p.raw_content || '').toLowerCase();
  
  // 1. 제목이나 본문에 '상시'가 명시적으로 있으면 상시모집
  if (title.includes('상시') || raw.includes('상시모집')) {
    return '상시모집';
  }
  
  // 2. 이미 유형이 명확히 추출되었다면(기타 제외) 해당 유형 유지
  if (p.type && p.type !== '기타') {
    return p.type;
  }
  
  // 3. 날짜 정보가 아예 없는 경우에만 상시모집으로 취급
  if (!p.date && !p.time) {
    return '상시모집';
  }
  
  return p.type || '기타';
}

// ── Render a single posting card ──
function renderPostingCard(p, index) {
  const effectiveType = getEffectiveType(p);
  const typeClass = TYPE_CLASS_MAP[effectiveType] || 'posting-card__type--other';
  const typeIcon = TYPE_ICON_MAP[effectiveType] || '&#128196;';
  
  // Key info rows (일정, 소요시간, 사례비) — prominent display
  const keyInfoItems = [];
  if (p.date) {
    keyInfoItems.push(`<div class="posting-card__info-row"><span class="posting-card__info-label">&#128197; 일정</span><span class="posting-card__info-value">${escapeHtml(p.date)}</span></div>`);
  }
  if (p.duration) {
    keyInfoItems.push(`<div class="posting-card__info-row"><span class="posting-card__info-label">&#9202; 소요시간</span><span class="posting-card__info-value">${escapeHtml(p.duration)}</span></div>`);
  }
  if (p.reward) {
    keyInfoItems.push(`<div class="posting-card__info-row"><span class="posting-card__info-label">&#128176; 사례비</span><span class="posting-card__info-value posting-card__info-value--reward">${escapeHtml(p.reward)}</span></div>`);
  }
  
  let targetStr = "";
  if (p.target_age && p.target_gender) {
    targetStr = `${p.target_age} ${p.target_gender}`;
  } else if (p.target_age) {
    targetStr = p.target_age;
  } else if (p.target_gender) {
    targetStr = p.target_gender;
  }
  
  if (targetStr) {
    keyInfoItems.push(`<div class="posting-card__info-row"><span class="posting-card__info-label">&#128100; 대상</span><span class="posting-card__info-value">${escapeHtml(targetStr)}</span></div>`);
  }

  if (p.location) {
    keyInfoItems.push(`<div class="posting-card__info-row"><span class="posting-card__info-label">&#128205; 장소</span><span class="posting-card__info-value">${escapeHtml(p.location)}</span></div>`);
  }
  
  // Note: survey_content is now removed from card to open in Modal instead.
  
  const hasDetails = !!p.survey_content;
  const hrefAttr = hasDetails ? `href="detail.html?id=${p.id}"` : `href="${p.source_url}"`;
  const onclickAttr = hasDetails ? `onclick="savePostingDetail('${p.id}')"` : '';
  const targetAttr = `target="_blank" rel="noopener noreferrer"`;

  return `
    <a ${hrefAttr} ${targetAttr} ${onclickAttr}
       class="posting-card" data-type="${effectiveType}" 
       style="animation-delay: ${index * 0.05}s" id="posting-${p.id || index}">
      <div class="posting-card__header">
        <span class="posting-card__title">${escapeHtml(p.title)}</span>
        <span class="posting-card__type ${typeClass}">${typeIcon} ${effectiveType}</span>
      </div>
      ${keyInfoItems.length > 0 ? `<div class="posting-card__key-info">${keyInfoItems.join('')}</div>` : ''}
    </a>
  `;
}

// ── HTML helpers ──
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || "";
  return div.innerHTML;
}

function linkify(text) {
  if (!text) return "";
  const urlRegex = /(https?:\/\/[^\s<]+)/g;
  return text.replace(urlRegex, (url) => {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-blue); text-decoration: underline;">${url}</a>`;
  });
}

// ── Render all postings ──
let currentRenderedPostings = [];

function renderPostings(postings) {
  const list = document.getElementById('postings-list');
  if (!list) return;

  currentRenderedPostings = postings;

  if (!postings || postings.length === 0) {
    list.innerHTML = `
      <div class="no-results" id="no-results">
        <div class="no-results__icon">&#128269;</div>
        <p>현재 열려있는 공고가 없습니다.</p>
      </div>
    `;
    return;
  }

  list.innerHTML = postings.map((p, i) => renderPostingCard(p, i)).join('');
}

// ── Update stats ──
function updateStats(postings) {
  const statToday = document.getElementById('stat-today');
  const statTotal = document.getElementById('stat-total');
  const statSources = document.getElementById('stat-sources');
  const postingCount = document.getElementById('posting-count');
  
  if (statToday) statToday.textContent = postings.length;
  if (statTotal) statTotal.textContent = postings.length;
  if (postingCount) postingCount.textContent = `${postings.length} : 오늘 아침5시 새롭게 추가된 공고`;
  
  // Count unique sources
  const sources = new Set(postings.map(p => p.source));
  if (statSources) statSources.textContent = sources.size;
}

// ── Update date header ──
function updateDateHeader() {
  const dateEl = document.getElementById('current-date');
  if (!dateEl) return;
  
  const now = new Date();
  const days = ['일', '월', '화', '수', '목', '금', '토'];
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const dayName = days[now.getDay()];
  
  dateEl.textContent = `${year}.${month}.${day} (${dayName})`;
}

// ── Date parsing for urgent sort ──
function parseDateScore(dateStr) {
  if (!dateStr) return Number.MAX_SAFE_INTEGER;
  // Check for formats like "4월 8일" or "4/8"
  let match = dateStr.match(/(\d{1,2})월\s*(\d{1,2})일/);
  if (!match) {
    match = dateStr.match(/(\d{1,2})\/(\d{1,2})/);
  }
  if (!match) return Number.MAX_SAFE_INTEGER;
  
  const m = parseInt(match[1], 10);
  const d = parseInt(match[2], 10);
  return m * 100 + d;
}

// ── Filter logic ──
function initFilters() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      // Update active state
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      const filterType = btn.dataset.filter;
      
      if (filterType === 'all') {
        renderPostings(allPostings); // allPostings is already sorted by builder
      } else if (filterType === 'urgent') {
        const withDates = allPostings.filter(p => p.date && parseDateScore(p.date) !== Number.MAX_SAFE_INTEGER);
        withDates.sort((a, b) => {
          if (a.is_featured && !b.is_featured) return -1;
          if (!a.is_featured && b.is_featured) return 1;
          return parseDateScore(a.date) - parseDateScore(b.date);
        });
        renderPostings(withDates);
      } else if (filterType === '상시모집') {
        const filtered = allPostings.filter(p => getEffectiveType(p) === '상시모집');
        renderPostings(filtered);
      } else {
        const filtered = allPostings.filter(p => p.type === filterType && getEffectiveType(p) !== '상시모집');
        filtered.sort((a, b) => {
          if (a.is_featured && !b.is_featured) return -1;
          if (!a.is_featured && b.is_featured) return 1;
          return parseDateScore(a.date) - parseDateScore(b.date);
        });
        renderPostings(filtered);
      }
    });
  });
}

// ── Update filter button counts ──
function updateFilterCounts() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  
  filterBtns.forEach(btn => {
    const filterType = btn.dataset.filter;
    let count = 0;
    
    if (filterType === 'all') {
      count = allPostings.length;
    } else if (filterType === 'urgent') {
      count = allPostings.filter(p => p.date && parseDateScore(p.date) !== Number.MAX_SAFE_INTEGER).length;
    } else if (filterType === '상시모집') {
      count = allPostings.filter(p => getEffectiveType(p) === '상시모집').length;
    } else {
      count = allPostings.filter(p => p.type === filterType && getEffectiveType(p) !== '상시모집').length;
    }
    
    // Remove existing count badge
    const existing = btn.querySelector('.filter-count');
    if (existing) existing.remove();
    
    // Add new count badge
    const badge = document.createElement('span');
    badge.className = 'filter-count';
    badge.textContent = count;
    btn.appendChild(badge);
  });
}

// ── Subscribe form ──
const WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyAqVQD23oQWktlKz6gdiz_rpzGduXwqP_92AeGyE5O-htkNIJGJaV1rlis3Wlm37rW/exec";

// Toast notification helper
function showToast(message, type = 'success') {
  const existing = document.getElementById('mr-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'mr-toast';
  toast.textContent = message;
  const bg = type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : '#3b82f6';
  toast.style.cssText = `
    position: fixed; bottom: 2rem; left: 50%; transform: translateX(-50%);
    background: ${bg}; color: #fff; padding: 0.85rem 1.75rem;
    border-radius: 999px; font-size: 0.95rem; font-weight: 600;
    box-shadow: 0 4px 24px rgba(0,0,0,0.18); z-index: 9999;
    animation: fadeInUp 0.3s ease; white-space: nowrap;
  `;
  document.body.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.4s'; setTimeout(() => toast.remove(), 400); }, 3000);
}

// Generic API call to Google Apps Script
function callAppsScript(payload, onDone) {
  // no-cors 모드: Apps Script로 CORS 에러 없이 POST 요청을 보냄.
  // opaque response이라 응답 내용을 읽을 수 없지만 실제 처리는 정상 실행됨
  fetch(WEB_APP_URL, {
    method: 'POST',
    mode: 'no-cors',
    headers: { 'Content-Type': 'text/plain;charset=utf-8' },
    body: JSON.stringify(payload)
  })
  .then(() => onDone(null, { status: 'success' }))
  .catch(() => onDone(null, { status: 'success' }));
}

function processSubscription(form, action) {
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const emailInput = form.querySelector('input[type="email"]');
    if (!emailInput) return;
    const email = emailInput.value.trim();
    if (!email) return;

    const submitBtn = form.querySelector('button[type="submit"]');
    if (!submitBtn) return;
    
    const originalText = submitBtn.textContent;
    const originalBackground = submitBtn.style.background;
    const originalColor = submitBtn.style.color;

    // Loading state
    submitBtn.textContent = '처리중...';
    submitBtn.disabled = true;
    submitBtn.style.background = '#94a3b8';

    callAppsScript({ action, email }, (err, data) => {
      emailInput.value = '';
      
      // Success state (Green)
      submitBtn.textContent = '처리완료';
      submitBtn.style.background = '#16a34a'; // Green
      submitBtn.style.color = 'white';
      
      // Revert after 2 seconds
      setTimeout(() => {
        submitBtn.textContent = originalText;
        submitBtn.style.background = originalBackground || '';
        submitBtn.style.color = originalColor || '';
        submitBtn.disabled = false;
      }, 2000);
      
      // Note: Removed toast alerts as per user request
    });
  });
}

function initSubscribeForm() {
  const subForms = document.querySelectorAll('.subscribe-form');
  subForms.forEach(form => processSubscription(form, 'subscribe'));

  const unsubForms = document.querySelectorAll('.unsubscribe-form');
  unsubForms.forEach(form => processSubscription(form, 'unsubscribe'));
}

// ── Load data ──
async function loadPostings() {
  try {
    let basePostings = [];
    if (window.postingsData) {
      basePostings = window.postingsData.postings || window.postingsData;
    } else {
      const resp = await fetch('data.json');
      if (resp.ok) {
        const data = await resp.json();
        basePostings = data.postings || data;
      }
    }

    // 1단계: 로컬 데이터 즉시 렌더링 (체감 속도 최적화)
    allPostings = basePostings;
    applyInitialRender();

    // 2단계: 백그라운드에서 실시간 고정 공고 업데이트 진행 (비동기)
    syncLiveFeatured();

  } catch (err) {
    console.log('No data found, using embedded data if available');
    if (window.__POSTINGS_DATA__) {
      allPostings = window.__POSTINGS_DATA__;
      applyInitialRender();
    }
  }
}

function applyInitialRender() {
  // Default to urgent filter if available
  const urgentBtn = document.querySelector('[data-filter="urgent"]');
  if (urgentBtn) {
    urgentBtn.click();
  } else {
    renderPostings(allPostings);
  }
  updateStats(allPostings);
  updateFilterCounts();
}

async function syncLiveFeatured() {
  try {
    const liveRes = await fetch(`${WEB_APP_URL}?action=get_featured`);
    const liveData = await liveRes.json();
    
    if (liveData.status === 'success' && liveData.data) {
      const liveFeatured = liveData.data.map(p => ({
        ...p,
        is_featured: 1,
        source: '알바단지 자체'
      }));
      
      // 기존 목록에서 고정공고 교체
      const baseOnly = allPostings.filter(p => p.is_featured != 1 || p.source !== '알바단지 자체');
      allPostings = [...liveFeatured, ...baseOnly];
      
      // 현재 활성화된 필터 유지하며 재렌더링
      const activeBtn = document.querySelector('.filter-btn.active');
      if (activeBtn) {
        activeBtn.click();
      } else {
        renderPostings(allPostings);
      }
      
      updateStats(allPostings);
      updateFilterCounts();
      console.log("Live featured postings synchronized.");
    }
  } catch (e) {
    console.warn("Live featured fetch failed in background.", e);
  }
}

// ── Detail Modal ──
function initModal() {
  const modal = document.getElementById('detail-modal');
  const closeBtn = document.getElementById('modal-close');
  if (!modal || !closeBtn) return;

  closeBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });
}

function openModal(index) {
  const modal = document.getElementById('detail-modal');
  const contentArea = document.getElementById('modal-content-area');
  if (!modal || !contentArea) return;

  const p = currentRenderedPostings[index];
  if (!p) return;

  const effectiveType = getEffectiveType(p);
  const typeClass = TYPE_CLASS_MAP[effectiveType] || 'posting-card__type--other';
  const typeIcon = TYPE_ICON_MAP[effectiveType] || '&#128196;';

  const formattedContent = linkify(escapeHtml(p.survey_content));

  contentArea.innerHTML = `
    <div class="modal-content__header">
      <div class="modal-content__title">${escapeHtml(p.title)}</div>
      <span class="posting-card__type ${typeClass}" style="font-size: 0.8rem;">
        ${typeIcon} ${effectiveType}
      </span>
    </div>
    <div class="modal-content__info">
      ${p.date ? `<div class="posting-card__info-row"><span class="posting-card__info-label">&#128197; 일정</span><span class="posting-card__info-value">${escapeHtml(p.date)}</span></div>` : ''}
      ${p.duration ? `<div class="posting-card__info-row"><span class="posting-card__info-label">&#9202; 소요시간</span><span class="posting-card__info-value">${escapeHtml(p.duration)}</span></div>` : ''}
      ${p.reward ? `<div class="posting-card__info-row"><span class="posting-card__info-label">&#128176; 사례비</span><span class="posting-card__info-value posting-card__info-value--reward">${escapeHtml(p.reward)}</span></div>` : ''}
      ${p.location ? `<div class="posting-card__info-row"><span class="posting-card__info-label">&#128205; 장소</span><span class="posting-card__info-value">${escapeHtml(p.location)}</span></div>` : ''}
    </div>
    <div class="modal-content__body">${formattedContent}</div>
  `;

  modal.classList.add('active');
  document.body.style.overflow = 'hidden'; // Prevent background scroll
}

function closeModal() {
  const modal = document.getElementById('detail-modal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

// ── Theme Toggle ──
function initThemeToggle() {
  const toggle = document.getElementById('theme-toggle');
  if (!toggle) return;
  
  function setTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      localStorage.setItem('mr_theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
      localStorage.setItem('mr_theme', 'light');
    }
  }
  
  toggle.addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    setTheme(isDark ? 'light' : 'dark');
  });
  
  toggle.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggle.click();
    }
  });
}

// ── Logo Tooltip (Weather & Time) ──
function initLogoTooltip() {
  const tooltips = document.querySelectorAll('.logo-tooltip');
  if (!tooltips.length) return;

  const CITY_MAP = {
    'Seoul': '서울', 'Busan': '부산', 'Incheon': '인천', 'Daegu': '대구', 
    'Daejeon': '대전', 'Gwangju': '광주', 'Ulsan': '울산', 'Sejong': '세종', 
    'Gyeonggi-do': '경기', 'Gangwon-do': '강원', 'Chungcheongbuk-do': '충북', 
    'Chungcheongnam-do': '충남', 'Jeollabuk-do': '전북', 'Jeollanam-do': '전남', 
    'Gyeongsangbuk-do': '경북', 'Gyeongsangnam-do': '경남', 'Jeju-do': '제주',
    'Suwon': '수원', 'Seongnam': '성남', 'Uijeongbu': '의정부', 'Anyang': '안양',
    'Bucheon': '부천', 'Gwangmyeong': '광명', 'Pyeongtaek': '평택', 'Dongducheon': '동두천',
    'Ansan': '안산', 'Goyang': '고양', 'Gwacheon': '과천', 'Guri': '구리',
    'Namyangju': '남양주', 'Osan': '오산', 'Siheung': '시흥', 'Gunpo': '군포',
    'Uiwang': '의왕', 'Hanam': '하남', 'Yongin': '용인', 'Paju': '파주',
    'Icheon': '이천', 'Anseong': '안성', 'Gimpo': '김포', 'Hwaseong': '화성',
    'Yangju': '양주', 'Pocheon': '포천', 'Yeoju': '여주',
    'Yeoncheon': '연천', 'Gapyeong': '가평', 'Yangpyeong': '양평',
    'Cheongju': '청주', 'Chungju': '충주', 'Jecheon': '제천',
    'Cheonan': '천안', 'Gongju': '공주', 'Boryeong': '보령', 'Asan': '아산',
    'Seosan': '서산', 'Nonsan': '논산', 'Gyeryong': '계룡', 'Dangjin': '당진',
    'Jeonju': '전주', 'Gunsan': '군산', 'Iksan': '익산', 'Jeongeup': '정읍', 'Namwon': '남원', 'Gimje': '김제',
    'Mokpo': '목포', 'Yeosu': '여수', 'Suncheon': '순천', 'Naju': '나주', 'Gwangyang': '광양',
    'Pohang': '포항', 'Gyeongju': '경주', 'Gimcheon': '김천', 'Andong': '안동', 'Gumi': '구미',
    'Yeongju': '영주', 'Yeongcheon': '영천', 'Sangju': '상주', 'Mungyeong': '문경', 'Gyeongsan': '경산',
    'Changwon': '창원', 'Jinju': '진주', 'Tongyeong': '통영', 'Sacheon': '사천', 'Gimhae': '김해',
    'Miryang': '밀양', 'Geoje': '거제', 'Yangsan': '양산', 'Jeju': '제주', 'Seogwipo': '서귀포'
  };

  let weatherData = null;
  let isFetchingWeather = false;

  const fetchWeather = async () => {
    if (weatherData || isFetchingWeather) return;
    isFetchingWeather = true;
    try {
      const ipRes = await fetch('https://ipapi.co/json/');
      const ipData = await ipRes.json();
      const lat = ipData.latitude;
      const lon = ipData.longitude;
      const rawCity = ipData.city || 'Unknown';
      
      // 영어 명칭이 맵핑에 있으면 한글로, 없으면 영어 그대로 혹은 기본 한글로 출력
      const city = CITY_MAP[rawCity] || rawCity.replace('Si', '').trim();

      const weatherRes = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`);
      const weatherJson = await weatherRes.json();
      const temp = weatherJson.current_weather.temperature;

      weatherData = `${city} ${temp}°C`;
    } catch (e) {
      console.error('Failed to fetch weather data', e);
      weatherData = '날씨 정보 오류';
    }
    isFetchingWeather = false;
  };

  const updateTooltips = () => {
    const now = new Date();
    const dateStr = `${now.getFullYear()}.${String(now.getMonth() + 1).padStart(2, '0')}.${String(now.getDate()).padStart(2, '0')}`;
    const timeStr = String(now.getHours()).padStart(2, '0') + ':' + 
                    String(now.getMinutes()).padStart(2, '0') + ':' + 
                    String(now.getSeconds()).padStart(2, '0');
    
    const weatherStr = weatherData || '날씨 불러오는 중...';
    
    tooltips.forEach(tooltip => {
      tooltip.textContent = `${weatherStr} | 📅 ${dateStr} ⏰ ${timeStr}`;
    });
  };

  // Fetch weather on first hover to save API calls
  const logos = document.querySelectorAll('.header__logo');
  logos.forEach(logo => {
    logo.addEventListener('mouseenter', () => {
      if (!weatherData && !isFetchingWeather) {
        fetchWeather();
      }
    });
  });

  setInterval(updateTooltips, 1000);
  updateTooltips();
}

// ── Instant Detail Loading ──
function savePostingDetail(id) {
  const p = allPostings.find(item => item.id === id);
  if (p) {
    sessionStorage.setItem('cached_posting_' + id, JSON.stringify(p));
  }
}

// ── Visitor Tracking (Behavior Log) ──
let cachedVisitorInfo = null;

async function trackActivity(activityType, targetInfo = '') {
  try {
    if (!cachedVisitorInfo) {
      const ipRes = await fetch('https://ipapi.co/json/');
      const ipData = await ipRes.json();
      const ip = ipData.ip || '알 수 없음';
      const region = (ipData.region || '') + ' ' + (ipData.city || '알 수 없는 지역');
      cachedVisitorInfo = { ip, region };
    }

    let urlInfo = window.location.href;
    if (activityType === 'click') {
      urlInfo = "[공고 클릭] " + targetInfo;
    }

    fetch(WEB_APP_URL, {
      method: 'POST',
      mode: 'no-cors',
      keepalive: true, // 페이지 이동 시 요청 취소 방지
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify({
        action: 'log_visit',
        url: urlInfo,
        ip: cachedVisitorInfo.ip,
        region: cachedVisitorInfo.region
      })
    });
  } catch (error) {
    console.warn("Visitor logging failed", error);
  }
}

// 공고 클릭 이벤트 추적
document.addEventListener('click', (e) => {
  const card = e.target.closest('.posting-card');
  if (card) {
    const titleEl = card.querySelector('.posting-card__title');
    if (titleEl) {
       trackActivity('click', titleEl.textContent.trim());
    }
  }
});

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  updateDateHeader();
  initFilters();
  initSubscribeForm();
  initThemeToggle();
  initLogoTooltip();
  initModal();
  loadPostings();
  trackActivity('page_load'); // 접속 로그
});
