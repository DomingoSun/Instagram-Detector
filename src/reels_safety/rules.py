"""Rule definitions for the Instagram policy compliance checker.

兩大類依據：

* **社群守則（Community Guidelines）** — 違反會被下架、警告、停權
  （consequence = REMOVAL）。
* **推薦準則（Recommendation Guidelines）與垃圾行為訊號** — 不會直接下架，
  但內容不會被推薦到 Reels/探索頁，也就是俗稱的「限流」
  （consequence = REACH）。

規則以高精確度為優先，支援中文（繁/簡通用字型樣）與英文。
Instagram 的執行細節會變動，規則僅供發佈前自我檢查參考。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from reels_safety.models import Consequence, Severity

# Categories
COMMUNITY = "community_guidelines"   # 社群守則違規（下架/停權風險）
RECOMMEND = "recommendation_limits"  # 推薦準則（限流風險）
SPAM = "spam_signals"                # 垃圾行為訊號（限流/帳號風險）
HASHTAG = "hashtag_risk"             # Hashtag 相關問題
DISCLOSURE = "disclosure"            # 商業內容揭露


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    consequence: Consequence
    severity: Severity
    pattern: re.Pattern
    message: str
    suggestion: str


def _rule(
    rule_id: str,
    category: str,
    consequence: Consequence,
    severity: Severity,
    pattern: str,
    message: str,
    suggestion: str,
) -> Rule:
    return Rule(
        rule_id, category, consequence, severity,
        re.compile(pattern, re.IGNORECASE), message, suggestion,
    )


TEXT_RULES: list[Rule] = [
    # ------------------------------------------------------------------
    # 社群守則：下架 / 停權風險
    # ------------------------------------------------------------------
    _rule(
        "cg.regulated_goods",
        COMMUNITY,
        Consequence.REMOVAL,
        Severity.HIGH,
        r"(買|賣|代購|出售|供應|下單).{0,12}(大麻|電子煙|菸油|煙油|處方藥|槍|彈藥)|"
        r"(大麻|電子煙|菸油|煙油|處方藥|槍枝)[^。\n]{0,12}(販售|出售|下單|私訊)|"
        r"(sell(ing)?|buy|dm\s+to\s+(buy|order)).{0,24}\b(weed|cannabis|vape(s|\s+juice)?|guns?|pills)\b",
        "提及買賣管制商品（藥品、電子煙、武器等），違反社群守則的受管制商品政策",
        "移除任何買賣管制商品的字句；即使只是玩笑或畫面帶到，也可能觸發下架與帳號警告",
    ),
    _rule(
        "cg.gambling_promo",
        COMMUNITY,
        Consequence.REMOVAL,
        Severity.HIGH,
        r"(娛樂城|線上賭場|博弈網|投注站|包贏|下注就送)|"
        r"(online\s+casino|betting\s+site|guaranteed\s+win).{0,20}(join|sign\s?up|link|註冊|加入)?",
        "宣傳博弈/線上賭場內容，未經授權的博弈推廣違反政策",
        "刪除博弈平台名稱、註冊連結與獲利誘因字句",
    ),
    _rule(
        "cg.financial_guarantee",
        COMMUNITY,
        Consequence.REMOVAL,
        Severity.HIGH,
        r"(保證獲利|穩賺不賠|翻倍|帶你上岸).{0,12}(投資|操盤|加入|私訊|老師)?|"
        r"(guaranteed|risk[- ]?free)\s+(profit|returns?)|double\s+your\s+(money|investment)",
        "保證獲利/穩賺不賠等投資宣稱，會被視為金融詐騙類內容",
        "拿掉任何保證報酬的字句；理財內容改用中性描述並加上風險提醒",
    ),
    _rule(
        "cg.adult_solicitation",
        COMMUNITY,
        Consequence.REMOVAL,
        Severity.HIGH,
        r"\b(onlyfans|0nlyfans)\b|(裸聊|約砲|援交)|(nudes?|porn)\b.{0,20}(link|dm|bio)",
        "成人內容導流/性交易暗示，違反裸露與性誘導政策",
        "移除相關字句與連結；性暗示內容即使不違規也會被排除在推薦之外",
    ),
    _rule(
        "cg.violence_threat",
        COMMUNITY,
        Consequence.REMOVAL,
        Severity.CRITICAL,
        r"i('| a|’)?m\s+going\s+to\s+(kill|hurt|beat)\s+you|你(給我)?(等著|死定了)|殺了(你|他)",
        "包含暴力威脅字句，違反暴力與煽動政策",
        "刪除威脅性語句；即使是開玩笑或戲劇效果，文字審查也可能直接下架",
    ),
    _rule(
        "cg.selfharm_content",
        COMMUNITY,
        Consequence.REMOVAL,
        Severity.CRITICAL,
        r"(how\s+to|ways\s+to)\s+(self[- ]?harm|hurt\s+(yourself|myself))|自殘(教學|方法)|輕生(方法|教學)",
        "涉及自殘/輕生方法的內容，屬最高風險違規",
        "完全移除相關內容；心理健康主題請改為求助資源導向的敘述",
    ),
    _rule(
        "cg.dangerous_challenge",
        COMMUNITY,
        Consequence.REMOVAL,
        Severity.HIGH,
        r"(blackout|choking|fire|benadryl|tide\s?pod|skull\s?breaker|milk\s?crate)\s*challenge|"
        r"(窒息|斷食|火焰)挑戰",
        "提及已知危險挑戰，危險行為內容會被下架且不被推薦",
        "避免拍攝或提及危險挑戰；特技類內容需明顯的專業/安全脈絡",
    ),
    # ------------------------------------------------------------------
    # 推薦準則：限流風險（內容不會被推薦到 Reels / 探索）
    # ------------------------------------------------------------------
    _rule(
        "reach.engagement_bait",
        RECOMMEND,
        Consequence.REACH,
        Severity.MEDIUM,
        r"(tag|標記|@)\s*\d*\s*(個)?(朋友|好友|friends?).{0,10}(抽|送|win)|"
        r"(按讚|點讚|留言|分享|追蹤|收藏)\s*[+＋加]?\s*(留言|分享|追蹤|收藏)?.{0,8}(就?抽|就送|抽獎)|"
        r"留言\s*[+＋]?\s*1|"
        r"\b(like|comment|share|follow)\b.{0,18}(to\s+win|for\s+a\s+chance|and\s+win)",
        "互動誘餌（要求按讚/留言/分享/標記朋友換獎勵），演算法會明確降低這類內容的觸及",
        "抽獎可以辦，但避免「按讚+分享才能抽」句式；改成自然的參與邀請，規則放留言區",
    ),
    _rule(
        "reach.health_claims",
        RECOMMEND,
        Consequence.REACH,
        Severity.HIGH,
        r"(保證|一定|絕對|百分百|100%)\s*(瘦|有效|見效|根治|治好)|"
        r"[\d一二三四五六七八九十兩半]+\s*(天|日|週|周|个月|個月|礼拜|禮拜)\s*(瘦|減|掉)\s*[\d一二三四五六七八九十兩半]+\s*(公斤|kg|斤)|"
        r"(根治|包治百病|無效退費)|"
        r"miracle\s+cure|lose\s+\d+\s*(lbs|pounds|kg)\s+in\s+\d+\s*(days?|weeks?)|cures?\s+(cancer|diabetes)",
        "誇大健康/減肥療效宣稱，屬於「不可推薦內容」，還可能觸發誤導性內容審查",
        "改用個人經驗描述（「我自己三個月的變化」）並避免保證性字眼與具體數字承諾",
    ),
    _rule(
        "reach.sexually_suggestive",
        RECOMMEND,
        Consequence.REACH,
        Severity.MEDIUM,
        r"擦邊|(福利|尺度)(照|影片|圖)|\bnsfw\b",
        "性暗示/擦邊內容不會被推薦系統分發，觸及只剩既有粉絲",
        "調整文案與畫面尺度；泳裝/健身內容避免鏡頭聚焦特定部位與挑逗字眼",
    ),
    _rule(
        "reach.clickbait",
        RECOMMEND,
        Consequence.REACH,
        Severity.LOW,
        r"你絕對(不敢|想不到|不會)相信|震驚|驚呆|99%\s*的人(都)?不知道|"
        r"you\s+won'?t\s+believe|shocking\s+truth|doctors\s+hate",
        "聳動標題黨用語，被歸類為低品質/誤導性內容訊號",
        "用具體價值點當開頭（「3 個讓拍攝更穩的技巧」）取代誇張驚嘆句",
    ),
    _rule(
        "reach.repost_watermark",
        RECOMMEND,
        Consequence.REACH,
        Severity.MEDIUM,
        r"(轉載|搬運|轉發)自|(tiktok|抖音).{0,10}(搬運|轉載|watermark|浮水印)|repost(ed)?\s+from",
        "轉載/搬運內容與帶其他平台浮水印的影片，Instagram 明確表示會降低推薦",
        "上傳無浮水印的原始檔；若在 TikTok 也發，先輸出無 logo 版本再各自上傳",
    ),
    # ------------------------------------------------------------------
    # 垃圾行為訊號
    # ------------------------------------------------------------------
    _rule(
        "spam.follow_bait",
        SPAM,
        Consequence.REACH,
        Severity.MEDIUM,
        r"互粉|互讚|回粉|\bf4f\b|follow4follow|like4like|\bl4l\b",
        "互粉/互讚字眼是典型垃圾帳號訊號，會拖累帳號整體權重",
        "刪除互粉互讚類字句，靠內容本身累積真實互動",
    ),
    _rule(
        "spam.buy_engagement",
        SPAM,
        Consequence.REMOVAL,
        Severity.MEDIUM,
        r"買粉|刷(粉|讚|留言)|(free|buy|cheap)\s+(followers|likes|views)",
        "提及買粉/刷量，違反平台真實性條款，帳號可能被限制或停權",
        "移除相關字句，且不要實際使用刷量服務——這是帳號被封最常見原因之一",
    ),
    _rule(
        "spam.offplatform_push",
        SPAM,
        Consequence.REACH,
        Severity.LOW,
        r"(加|\+|＋)\s*(賴|line|微信|wechat|telegram|tg)\b|私訊我?(領|拿|索取)|"
        r"https?://(t\.me|wa\.me|lin\.ee)/\S+",
        "把觀眾導流到站外通訊軟體（LINE/微信/Telegram），是演算法的垃圾/詐騙關聯訊號",
        "偶爾使用影響不大，但每支影片都導流會累積負面權重；連結建議放個人檔案而非文案",
    ),
    # ------------------------------------------------------------------
    # 商業內容揭露
    # ------------------------------------------------------------------
    _rule(
        "disclosure.paid_partnership",
        DISCLOSURE,
        Consequence.QUALITY,
        Severity.LOW,
        r"業配|廠商(提供|贊助|邀約)|品牌合作|(sponsored|#ad\b|#sponsored)|(這|本)(支|集|部)?(影片)?由.{0,12}(贊助|提供)",
        "內容涉及商業合作——若沒開啟官方標籤，可能違反品牌置入內容政策",
        "在發佈時開啟「付費合作關係（Paid partnership）」標籤，不要只在文案寫「業配」",
    ),
]


# ----------------------------------------------------------------------
# Hashtag 檢查
# ----------------------------------------------------------------------

# 文案中的 hashtag（支援中文標籤）
HASHTAG_IN_TEXT = re.compile(r"#([^\s#，。!！?？]+)")

# Instagram 的硬上限：超過 30 個 hashtag 貼文可能無法發佈
HASHTAG_HARD_LIMIT = 30
# 官方近年建議 3–5 個；超過這個數字開始像垃圾內容
HASHTAG_RECOMMENDED_MAX = 10

# 曾被廣泛回報遭封鎖/限制的 hashtag（節錄，非官方完整清單，會隨時間變動）。
# 使用被限制的 hashtag 可能讓貼文不出現在標籤頁與推薦中。
RESTRICTED_HASHTAGS = {
    "adulting", "alone", "always", "beautyblogger", "bikinibody", "boho",
    "brain", "curvygirls", "dating", "desk", "direct", "dm", "edm",
    "girlsonly", "hardworkpaysoff", "humpday", "killingit", "master",
    "models", "mustfollow", "newyears", "petite", "pushups", "single",
    "singlelife", "skateboarding", "snap", "snapchat", "sunbathing",
    "tag4like", "tagsforlikes", "valentinesday", "workflow",
}


# ----------------------------------------------------------------------
# 純文字檢測不到、發佈前需人工確認的項目
# ----------------------------------------------------------------------

MANUAL_CHECKLIST: list[str] = [
    "影片是否帶有其他平台浮水印（TikTok logo 等）？有浮水印的 Reels 會被明確降低推薦",
    "背景音樂是否來自 IG 音樂庫或已取得授權？版權偵測可能導致靜音、下架或觸及受限",
    "畫面中是否出現菸、酒、電子煙、賭博、血腥或過度裸露？畫面元素文字檢測不到，但會影響推薦資格",
    "是否為原創內容？重複搬運他人影片會被降低分發並可能收到版權申訴",
    "封面與開頭 3 秒是否與內容相符？誤導性封面屬於低品質訊號",
]
