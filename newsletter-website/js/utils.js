/**
 * Common Utilities and Constants for Albadanji
 */

const WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzyamQy2beFZ0_uDA6IEdAqQ5rG5AJ4o70wyiXNh9XegnNXv_4YeiNcT96ebamgl5SW/exec";

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

function getEffectiveType(p) {
  const title = (p.title || '').toLowerCase();
  const raw = (p.raw_content || '').toLowerCase();
  
  if (title.includes('상시') || raw.includes('상시모집')) {
    return '상시모집';
  }
  
  if (p.type && p.type !== '기타') {
    return p.type;
  }
  
  if (!p.date && !p.time) {
    return '상시모집';
  }
  
  return p.type || '기타';
}
