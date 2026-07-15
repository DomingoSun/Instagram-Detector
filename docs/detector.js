/* Reels 發佈前政策檢查 — 瀏覽器版規則引擎
 * 與 Python 版 (src/reels_safety/rules.py, analyzer.py) 對應的 JS 移植。
 * 規則若有調整，兩邊需同步。 */

const SEVERITY_WEIGHT = { low: 8, medium: 18, high: 35, critical: 60 };
const REACH_SCORE_THRESHOLD = 30;
const HASHTAG_HARD_LIMIT = 30;
const HASHTAG_RECOMMENDED_MAX = 10;

const RESTRICTED_HASHTAGS = new Set([
  "adulting", "alone", "always", "beautyblogger", "bikinibody", "boho",
  "brain", "curvygirls", "dating", "desk", "direct", "dm", "edm",
  "girlsonly", "hardworkpaysoff", "humpday", "killingit", "master",
  "models", "mustfollow", "newyears", "petite", "pushups", "single",
  "singlelife", "skateboarding", "snap", "snapchat", "sunbathing",
  "tag4like", "tagsforlikes", "valentinesday", "workflow",
]);

const MANUAL_CHECKLIST = [
  "影片是否帶有其他平台浮水印（TikTok logo 等）？有浮水印的 Reels 會被明確降低推薦",
  "背景音樂是否來自 IG 音樂庫或已取得授權？版權偵測可能導致靜音、下架或觸及受限",
  "畫面中是否出現菸、酒、電子煙、賭博、血腥或過度裸露？畫面元素文字檢測不到，但會影響推薦資格",
  "是否為原創內容？重複搬運他人影片會被降低分發並可能收到版權申訴",
  "封面與開頭 3 秒是否與內容相符？誤導性封面屬於低品質訊號",
];

const RULES = [
  // ---- 社群守則：下架 / 停權風險 ----
  {
    id: "cg.regulated_goods", category: "community_guidelines",
    consequence: "removal", severity: "high",
    pattern: /(買|賣|代購|出售|供應|下單).{0,12}(大麻|電子煙|菸油|煙油|處方藥|槍|彈藥)|(大麻|電子煙|菸油|煙油|處方藥|槍枝)[^。\n]{0,12}(販售|出售|下單|私訊)|(sell(ing)?|buy|dm\s+to\s+(buy|order)).{0,24}\b(weed|cannabis|vape(s|\s+juice)?|guns?|pills)\b/i,
    message: "提及買賣管制商品（藥品、電子煙、武器等），違反社群守則的受管制商品政策",
    suggestion: "移除任何買賣管制商品的字句；即使只是玩笑或畫面帶到，也可能觸發下架與帳號警告",
  },
  {
    id: "cg.gambling_promo", category: "community_guidelines",
    consequence: "removal", severity: "high",
    pattern: /(娛樂城|線上賭場|博弈網|投注站|包贏|下注就送)|(online\s+casino|betting\s+site|guaranteed\s+win).{0,20}(join|sign\s?up|link|註冊|加入)?/i,
    message: "宣傳博弈/線上賭場內容，未經授權的博弈推廣違反政策",
    suggestion: "刪除博弈平台名稱、註冊連結與獲利誘因字句",
  },
  {
    id: "cg.financial_guarantee", category: "community_guidelines",
    consequence: "removal", severity: "high",
    pattern: /(保證獲利|穩賺不賠|翻倍|帶你上岸).{0,12}(投資|操盤|加入|私訊|老師)?|(guaranteed|risk[- ]?free)\s+(profit|returns?)|double\s+your\s+(money|investment)/i,
    message: "保證獲利/穩賺不賠等投資宣稱，會被視為金融詐騙類內容",
    suggestion: "拿掉任何保證報酬的字句；理財內容改用中性描述並加上風險提醒",
  },
  {
    id: "cg.adult_solicitation", category: "community_guidelines",
    consequence: "removal", severity: "high",
    pattern: /\b(onlyfans|0nlyfans)\b|(裸聊|約砲|援交)|(nudes?|porn)\b.{0,20}(link|dm|bio)/i,
    message: "成人內容導流/性交易暗示，違反裸露與性誘導政策",
    suggestion: "移除相關字句與連結；性暗示內容即使不違規也會被排除在推薦之外",
  },
  {
    id: "cg.violence_threat", category: "community_guidelines",
    consequence: "removal", severity: "critical",
    pattern: /i('| a|’)?m\s+going\s+to\s+(kill|hurt|beat)\s+you|你(給我)?(等著|死定了)|殺了(你|他)/i,
    message: "包含暴力威脅字句，違反暴力與煽動政策",
    suggestion: "刪除威脅性語句；即使是開玩笑或戲劇效果，文字審查也可能直接下架",
  },
  {
    id: "cg.selfharm_content", category: "community_guidelines",
    consequence: "removal", severity: "critical",
    pattern: /(how\s+to|ways\s+to)\s+(self[- ]?harm|hurt\s+(yourself|myself))|自殘(教學|方法)|輕生(方法|教學)/i,
    message: "涉及自殘/輕生方法的內容，屬最高風險違規",
    suggestion: "完全移除相關內容；心理健康主題請改為求助資源導向的敘述",
  },
  {
    id: "cg.dangerous_challenge", category: "community_guidelines",
    consequence: "removal", severity: "high",
    pattern: /(blackout|choking|fire|benadryl|tide\s?pod|skull\s?breaker|milk\s?crate)\s*challenge|(窒息|斷食|火焰)挑戰/i,
    message: "提及已知危險挑戰，危險行為內容會被下架且不被推薦",
    suggestion: "避免拍攝或提及危險挑戰；特技類內容需明顯的專業/安全脈絡",
  },
  // ---- 推薦準則：限流風險 ----
  {
    id: "reach.engagement_bait", category: "recommendation_limits",
    consequence: "reach", severity: "medium",
    pattern: /(tag|標記|@)\s*\d*\s*(個)?(朋友|好友|friends?).{0,10}(抽|送|win)|(按讚|點讚|留言|分享|追蹤|收藏)\s*[+＋加]?\s*(留言|分享|追蹤|收藏)?.{0,8}(就?抽|就送|抽獎)|留言\s*[+＋]?\s*1|\b(like|comment|share|follow)\b.{0,18}(to\s+win|for\s+a\s+chance|and\s+win)/i,
    message: "互動誘餌（要求按讚/留言/分享/標記朋友換獎勵），演算法會明確降低這類內容的觸及",
    suggestion: "抽獎可以辦，但避免「按讚+分享才能抽」句式；改成自然的參與邀請，規則放留言區",
  },
  {
    id: "reach.health_claims", category: "recommendation_limits",
    consequence: "reach", severity: "high",
    pattern: /(保證|一定|絕對|百分百|100%)\s*(瘦|有效|見效|根治|治好)|[\d一二三四五六七八九十兩半]+\s*(天|日|週|周|个月|個月|礼拜|禮拜)\s*(瘦|減|掉)\s*[\d一二三四五六七八九十兩半]+\s*(公斤|kg|斤)|(根治|包治百病|無效退費)|miracle\s+cure|lose\s+\d+\s*(lbs|pounds|kg)\s+in\s+\d+\s*(days?|weeks?)|cures?\s+(cancer|diabetes)/i,
    message: "誇大健康/減肥療效宣稱，屬於「不可推薦內容」，還可能觸發誤導性內容審查",
    suggestion: "改用個人經驗描述（「我自己三個月的變化」）並避免保證性字眼與具體數字承諾",
  },
  {
    id: "reach.sexually_suggestive", category: "recommendation_limits",
    consequence: "reach", severity: "medium",
    pattern: /擦邊|(福利|尺度)(照|影片|圖)|\bnsfw\b/i,
    message: "性暗示/擦邊內容不會被推薦系統分發，觸及只剩既有粉絲",
    suggestion: "調整文案與畫面尺度；泳裝/健身內容避免鏡頭聚焦特定部位與挑逗字眼",
  },
  {
    id: "reach.clickbait", category: "recommendation_limits",
    consequence: "reach", severity: "low",
    pattern: /你絕對(不敢|想不到|不會)相信|震驚|驚呆|99%\s*的人(都)?不知道|you\s+won'?t\s+believe|shocking\s+truth|doctors\s+hate/i,
    message: "聳動標題黨用語，被歸類為低品質/誤導性內容訊號",
    suggestion: "用具體價值點當開頭（「3 個讓拍攝更穩的技巧」）取代誇張驚嘆句",
  },
  {
    id: "reach.repost_watermark", category: "recommendation_limits",
    consequence: "reach", severity: "medium",
    pattern: /(轉載|搬運|轉發)自|(tiktok|抖音).{0,10}(搬運|轉載|watermark|浮水印)|repost(ed)?\s+from/i,
    message: "轉載/搬運內容與帶其他平台浮水印的影片，Instagram 明確表示會降低推薦",
    suggestion: "上傳無浮水印的原始檔；若在 TikTok 也發，先輸出無 logo 版本再各自上傳",
  },
  // ---- 垃圾行為訊號 ----
  {
    id: "spam.follow_bait", category: "spam_signals",
    consequence: "reach", severity: "medium",
    pattern: /互粉|互讚|回粉|\bf4f\b|follow4follow|like4like|\bl4l\b/i,
    message: "互粉/互讚字眼是典型垃圾帳號訊號，會拖累帳號整體權重",
    suggestion: "刪除互粉互讚類字句，靠內容本身累積真實互動",
  },
  {
    id: "spam.buy_engagement", category: "spam_signals",
    consequence: "removal", severity: "medium",
    pattern: /買粉|刷(粉|讚|留言)|(free|buy|cheap)\s+(followers|likes|views)/i,
    message: "提及買粉/刷量，違反平台真實性條款，帳號可能被限制或停權",
    suggestion: "移除相關字句，且不要實際使用刷量服務——這是帳號被封最常見原因之一",
  },
  {
    id: "spam.offplatform_push", category: "spam_signals",
    consequence: "reach", severity: "low",
    pattern: /(加|\+|＋)\s*(賴|line|微信|wechat|telegram|tg)\b|私訊我?(領|拿|索取)|https?:\/\/(t\.me|wa\.me|lin\.ee)\/\S+/i,
    message: "把觀眾導流到站外通訊軟體（LINE/微信/Telegram），是演算法的垃圾/詐騙關聯訊號",
    suggestion: "偶爾使用影響不大，但每支影片都導流會累積負面權重；連結建議放個人檔案而非文案",
  },
  // ---- 商業內容揭露 ----
  {
    id: "disclosure.paid_partnership", category: "disclosure",
    consequence: "quality", severity: "low",
    pattern: /業配|廠商(提供|贊助|邀約)|品牌合作|(sponsored|#ad\b|#sponsored)|(這|本)(支|集|部)?(影片)?由.{0,12}(贊助|提供)/i,
    message: "內容涉及商業合作——若沒開啟官方標籤，可能違反品牌置入內容政策",
    suggestion: "在發佈時開啟「付費合作關係（Paid partnership）」標籤，不要只在文案寫「業配」",
  },
];

const HASHTAG_IN_TEXT = /#([^\s#，。!！?？]+)/g;

function snippet(text, start, end) {
  const lo = Math.max(0, start - 20);
  const hi = Math.min(text.length, end + 20);
  let s = text.slice(lo, hi).trim().replace(/\n/g, " ");
  if (s.length > 120) s = s.slice(0, 120) + "…";
  return s;
}

function runTextRules(field, text) {
  const detections = [];
  for (const rule of RULES) {
    const m = rule.pattern.exec(text);
    if (m) {
      detections.push({
        category: rule.category, consequence: rule.consequence,
        severity: rule.severity, rule_id: rule.id,
        message: rule.message, suggestion: rule.suggestion,
        field, evidence: snippet(text, m.index, m.index + m[0].length),
      });
    }
  }
  return detections;
}

function collectHashtags(caption, extraTags) {
  const tags = (extraTags || [])
    .map((h) => h.replace(/^#+/, "").toLowerCase())
    .filter(Boolean);
  for (const m of caption.matchAll(HASHTAG_IN_TEXT)) tags.push(m[1].toLowerCase());
  return tags;
}

function checkHashtags(caption, extraTags) {
  const tags = collectHashtags(caption, extraTags);
  if (!tags.length) return [];
  const detections = [];
  const det = (severity, id, message, suggestion, evidence) =>
    detections.push({
      category: "hashtag_risk", consequence: "reach", severity,
      rule_id: id, message, suggestion, field: "hashtags", evidence,
    });

  if (tags.length > HASHTAG_HARD_LIMIT) {
    det("high", "hashtag.over_hard_limit",
      `共 ${tags.length} 個 hashtag，超過 Instagram 上限 ${HASHTAG_HARD_LIMIT} 個，貼文可能無法發佈或被直接判為垃圾內容`,
      "刪減到 3–5 個最相關的標籤", `${tags.length} tags`);
  } else if (tags.length > HASHTAG_RECOMMENDED_MAX) {
    det("low", "hashtag.too_many",
      `共 ${tags.length} 個 hashtag，堆疊大量標籤是垃圾內容訊號`,
      "官方建議 3–5 個精準標籤，效果優於大量廣撒", `${tags.length} tags`);
  }

  const restricted = [...new Set(tags)].filter((t) => RESTRICTED_HASHTAGS.has(t)).sort();
  if (restricted.length) {
    det("medium", "hashtag.restricted",
      "使用了曾被回報遭封鎖/限制的 hashtag，貼文可能不會出現在標籤頁與推薦中",
      "發佈前到 IG 搜尋該標籤：若標籤頁顯示異常或搜不到，就換掉；清單會隨時間變動",
      restricted.map((t) => `#${t}`).join(", "));
  }

  const seen = new Set();
  const dupes = [...new Set(tags.filter((t) => seen.has(t) || (seen.add(t), false)))].sort();
  if (dupes.length) {
    det("low", "hashtag.duplicates", "有重複的 hashtag",
      "移除重複標籤，重複堆疊沒有加成、只有垃圾訊號",
      dupes.map((t) => `#${t}`).join(", "));
  }
  return detections;
}

function analyze({ caption = "", transcript = "", hashtags = [] }) {
  const detections = [];
  if (caption) detections.push(...runTextRules("caption", caption));
  if (transcript) detections.push(...runTextRules("audio_transcript", transcript));
  if (hashtags.length) {
    detections.push(...runTextRules("hashtags", hashtags.map((h) => `#${h.replace(/^#+/, "")}`).join(" ")));
  }
  detections.push(...checkHashtags(caption, hashtags));

  const seen = new Set();
  let score = 0;
  let reachScore = 0;
  for (const d of detections) {
    const key = `${d.rule_id}|${d.field}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const w = SEVERITY_WEIGHT[d.severity];
    score += w;
    if (d.consequence === "reach") reachScore += w;
  }
  score = Math.min(score, 100);

  const removalHits = detections.filter((d) => d.consequence === "removal");
  let verdict;
  if (removalHits.some((d) => d.severity === "high" || d.severity === "critical")) {
    verdict = "violation_risk";
  } else if (
    removalHits.length ||
    reachScore >= REACH_SCORE_THRESHOLD ||
    detections.some((d) => d.consequence === "reach" && (d.severity === "medium" || d.severity === "high"))
  ) {
    verdict = "reach_risk";
  } else if (detections.length) {
    verdict = "review";
  } else {
    verdict = "pass";
  }

  detections.sort((a, b) => SEVERITY_WEIGHT[b.severity] - SEVERITY_WEIGHT[a.severity]);
  return { verdict, risk_score: score, detections };
}

/* ---- 簡體 → 繁體正規化 ----
 * 語音辨識（Whisper）輸出的中文多為簡體，而規則字典是繁體。
 * 這裡只轉換規則中會用到的字，先處理有歧義的詞（赞助→贊助 vs 按赞→按讚），
 * 再做單字對應，不是完整的簡繁轉換器。 */

const ZH_WORD_MAP = [
  ["赞助", "贊助"],
  ["按赞", "按讚"], ["点赞", "點讚"], ["互赞", "互讚"], ["刷赞", "刷讚"],
];

const ZH_CHAR_MAP = {
  "证": "證", "获": "獲", "稳": "穩", "赚": "賺", "赔": "賠", "电": "電",
  "烟": "煙", "药": "藥", "处": "處", "枪": "槍", "弹": "彈", "买": "買",
  "卖": "賣", "购": "購", "单": "單", "讯": "訊", "赌": "賭", "场": "場",
  "娱": "娛", "乐": "樂", "网": "網", "赢": "贏", "带": "帶", "约": "約",
  "炮": "砲", "杀": "殺", "残": "殘", "轻": "輕", "学": "學", "断": "斷",
  "战": "戰", "标": "標", "记": "記", "个": "個", "点": "點", "转": "轉",
  "载": "載", "运": "運", "发": "發", "奖": "獎", "赖": "賴", "线": "線",
  "领": "領", "业": "業", "厂": "廠", "边": "邊", "绝": "絕", "对": "對",
  "见": "見", "无": "無", "费": "費", "惊": "驚", "踪": "蹤", "着": "著",
  "赞": "讚", "减": "減", "赛": "賽", "岁": "歲", "钱": "錢", "货": "貨",
};

function zhNormalize(text) {
  let out = text;
  for (const [from, to] of ZH_WORD_MAP) out = out.split(from).join(to);
  return out.replace(/[一-鿿]/g, (ch) => ZH_CHAR_MAP[ch] || ch);
}

/* ---- 帶時間戳的逐字稿分段檢測 ----
 * segments: [{ start, end, text }]（秒），回傳每段命中的規則與時間。 */

function formatTime(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return "--:--";
  const s = Math.max(0, Math.round(seconds));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function analyzeSegments(segments) {
  const findings = [];
  for (const seg of segments) {
    const text = zhNormalize(seg.text || "");
    if (!text.trim()) continue;
    for (const rule of RULES) {
      const m = rule.pattern.exec(text);
      if (m) {
        findings.push({
          start: seg.start, end: seg.end,
          time: `${formatTime(seg.start)}–${formatTime(seg.end)}`,
          match: m[0].trim(),
          segment_text: text.trim(),
          rule_id: rule.id, category: rule.category,
          consequence: rule.consequence, severity: rule.severity,
          message: rule.message, suggestion: rule.suggestion,
        });
      }
    }
  }
  findings.sort((a, b) => (a.start ?? 0) - (b.start ?? 0));
  return findings;
}

if (typeof module !== "undefined") {
  module.exports = {
    analyze, collectHashtags, MANUAL_CHECKLIST, RULES,
    zhNormalize, analyzeSegments, formatTime,
  };
}
