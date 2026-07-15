"""Rule definitions: keyword/regex patterns grouped by safety category.

Each rule is a compiled regex with a category, severity, and human-readable
message. Rules are intentionally conservative — the goal of the MVP is high
precision on obviously risky content, not exhaustive recall.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from reels_safety.models import Severity

# Categories
SCAM = "scam_fraud"
PHISHING = "phishing_links"
DANGEROUS_CHALLENGE = "dangerous_challenge"
ADULT = "adult_content"
SELF_HARM = "self_harm"
HARASSMENT = "hate_harassment"
SPAM = "spam_engagement_bait"


@dataclass(frozen=True)
class Rule:
    rule_id: str
    category: str
    severity: Severity
    pattern: re.Pattern
    message: str


def _rule(rule_id: str, category: str, severity: Severity, pattern: str, message: str) -> Rule:
    return Rule(rule_id, category, severity, re.compile(pattern, re.IGNORECASE), message)


TEXT_RULES: list[Rule] = [
    # --- Scam / fraud ---
    _rule(
        "scam.guaranteed_returns",
        SCAM,
        Severity.HIGH,
        r"(guaranteed|risk[- ]?free)\s+(profit|return|income|money)|double\s+your\s+(money|investment|crypto|btc)",
        "Promises of guaranteed or doubled returns, a hallmark of investment scams",
    ),
    _rule(
        "scam.crypto_giveaway",
        SCAM,
        Severity.HIGH,
        r"(free|giving\s+away|giveaway).{0,30}\b(btc|bitcoin|eth|ethereum|crypto|usdt|nft)\b|"
        r"\b(btc|bitcoin|eth|ethereum|crypto|usdt|nft)\b.{0,30}(giveaway|airdrop)",
        "Crypto giveaway/airdrop language commonly used in fraud",
    ),
    _rule(
        "scam.get_rich_quick",
        SCAM,
        Severity.MEDIUM,
        r"(make|earn)\s+\$?\d[\d,]*\s*(per|a|/)\s*(day|week|hour)|passive\s+income\s+(secret|hack|trick)|get\s+rich\s+quick",
        "Get-rich-quick earnings claims",
    ),
    _rule(
        "scam.dm_to_invest",
        SCAM,
        Severity.HIGH,
        r"(dm|message|text|whatsapp|telegram)\s+(me|us|now|here).{0,40}(invest|profit|earn|trade|trading|forex|crypto|signal)|"
        r"(invest|profit|earn|trade|trading|forex|crypto|signal).{0,40}(dm|message|text)\s+(me|us|now)",
        "Solicits direct messages for investment/trading opportunities",
    ),
    _rule(
        "scam.advance_fee",
        SCAM,
        Severity.HIGH,
        r"(send|pay|deposit)\s+(a\s+)?(small\s+)?(fee|deposit|amount).{0,40}(receive|unlock|claim|get)|"
        r"(claim|unlock)\s+your\s+(prize|reward|winnings)",
        "Advance-fee / prize-claim scam language",
    ),
    _rule(
        "scam.cashapp_flip",
        SCAM,
        Severity.HIGH,
        r"(cash\s?app|venmo|paypal|zelle)\s*(flip|blessing)|money\s+flip",
        "Payment-app 'flip' scam",
    ),
    # --- Dangerous challenges / harmful acts ---
    _rule(
        "danger.challenge",
        DANGEROUS_CHALLENGE,
        Severity.HIGH,
        r"(blackout|choking|fire|benadryl|tide\s?pod|skull\s?breaker|milk\s?crate|blue\s?whale|pass[- ]?out)\s*challenge",
        "References a known dangerous viral challenge",
    ),
    _rule(
        "danger.try_at_home",
        DANGEROUS_CHALLENGE,
        Severity.MEDIUM,
        r"(try\s+this\s+at\s+home).{0,40}(fire|knife|explos|chemical|bleach)|"
        r"(fire|knife|explos|chemical|bleach).{0,40}try\s+this\s+at\s+home",
        "Encourages replicating hazardous activity at home",
    ),
    # --- Adult content ---
    _rule(
        "adult.explicit_solicitation",
        ADULT,
        Severity.HIGH,
        r"\b(onlyfans|0nlyfans|only\s?fans)\b.{0,40}(link|bio|dm|free|leak)|"
        r"(nude|nudes|xxx|porn|p0rn)\b.{0,30}(link|bio|dm|free|sale)",
        "Solicits or links to explicit adult content",
    ),
    _rule(
        "adult.explicit_keywords",
        ADULT,
        Severity.MEDIUM,
        r"\b(xxx|porn|p0rn|nsfw)\b",
        "Explicit adult-content keywords",
    ),
    # --- Self-harm ---
    _rule(
        "selfharm.encouragement",
        SELF_HARM,
        Severity.CRITICAL,
        r"(kill\s+(yourself|urself)|kys\b|you\s+should\s+(die|end\s+it))",
        "Encourages self-harm or suicide directed at a person",
    ),
    _rule(
        "selfharm.promotion",
        SELF_HARM,
        Severity.HIGH,
        r"(how\s+to|ways\s+to)\s+(self[- ]?harm|hurt\s+(yourself|myself))|pro[- ]?ana\b|thinspo\b",
        "Promotes or instructs self-harm / eating-disorder content",
    ),
    # --- Hate / harassment ---
    _rule(
        "harassment.threat",
        HARASSMENT,
        Severity.CRITICAL,
        r"i('| a|’)?m\s+going\s+to\s+(kill|hurt|beat|find)\s+you|watch\s+your\s+back|you('re|r|\s+are)\s+dead\b",
        "Direct threat of violence",
    ),
    _rule(
        "harassment.doxxing",
        HARASSMENT,
        Severity.HIGH,
        r"(here('s| is)\s+(his|her|their)\s+(address|phone|number)|expose\s+(him|her|them).{0,30}(address|school|work))",
        "Shares or threatens to share private identifying information",
    ),
    # --- Spam / engagement bait ---
    _rule(
        "spam.follow_bait",
        SPAM,
        Severity.LOW,
        r"(follow\s+(me|us)\s+(and|to)\s+(win|get|claim))|f4f\b|follow4follow|like4like|l4l\b",
        "Follow/like-for-reward engagement bait",
    ),
    _rule(
        "spam.link_in_bio_pressure",
        SPAM,
        Severity.LOW,
        r"(link\s+in\s+bio).{0,40}(now|hurry|limited|before\s+it('s| is)\s+gone|only\s+\d+\s+(left|spots))",
        "High-pressure 'link in bio' call to action",
    ),
    _rule(
        "spam.free_followers",
        SPAM,
        Severity.MEDIUM,
        r"(free|buy)\s+(followers|likes|views)\b",
        "Promotes follower/like-buying services",
    ),
]


# --- Link rules (applied to URLs extracted from any text field) ---

URL_PATTERN = re.compile(r"https?://[^\s)\]}>\"']+|(?<![\w.])(?:www\.)[^\s)\]}>\"']+", re.IGNORECASE)

URL_SHORTENERS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "is.gd",
    "cutt.ly",
    "rb.gy",
    "shorturl.at",
    "linktr.ee",  # not inherently bad, but hides destination — LOW severity handled below
}

# Domains that impersonate well-known platforms (lookalike spellings).
LOOKALIKE_PATTERN = re.compile(
    r"(insta9ram|1nstagram|instagram-[a-z0-9-]*\.(?!com)|faceb00k|te1egram|whatsapp-[a-z0-9-]*\.(?!com)|"
    r"wh4tsapp|paypa1|g00gle|amaz0n)",
    re.IGNORECASE,
)

MESSAGING_APP_DOMAINS = ("t.me", "wa.me", "chat.whatsapp.com")

MONEY_CONTEXT = re.compile(
    r"(invest|profit|earn|crypto|btc|forex|trading|signal|cash|money|rich|payout)", re.IGNORECASE
)
