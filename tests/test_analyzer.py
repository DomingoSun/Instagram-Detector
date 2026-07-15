import pytest

from reels_safety import analyze
from reels_safety.models import ReelContent, Verdict


def result_for(**kwargs):
    return analyze(ReelContent(**kwargs))


class TestSafeContent:
    def test_empty_content_is_safe(self):
        result = result_for(caption="")
        assert result.verdict is Verdict.SAFE
        assert result.risk_score == 0
        assert result.detections == []

    def test_ordinary_caption_is_safe(self):
        result = result_for(
            caption="Sunset run along the beach tonight 🌅 new PB!",
            hashtags=["running", "sunset", "fitness"],
        )
        assert result.verdict is Verdict.SAFE
        assert result.detections == []

    def test_normal_link_is_safe(self):
        result = result_for(caption="Full recipe on my blog: https://example.com/recipes/pasta")
        assert result.verdict is Verdict.SAFE


class TestScamDetection:
    def test_guaranteed_returns(self):
        result = result_for(caption="Guaranteed profit every week, join now!")
        assert any(d.rule_id == "scam.guaranteed_returns" for d in result.detections)
        assert result.verdict is not Verdict.SAFE

    def test_crypto_giveaway_with_telegram_link_is_unsafe(self):
        result = result_for(
            caption="FREE bitcoin giveaway!! DM me to invest, join https://t.me/fastprofits"
        )
        assert result.verdict is Verdict.UNSAFE
        categories = set(result.categories)
        assert "scam_fraud" in categories
        assert "phishing_links" in categories

    def test_cash_app_flip(self):
        result = result_for(comments=["cashapp flip $50 into $500, dm me"])
        assert any(d.rule_id == "scam.cashapp_flip" for d in result.detections)


class TestPhishing:
    def test_shortened_url_flagged_low(self):
        result = result_for(caption="check this out https://bit.ly/3xyz")
        det = next(d for d in result.detections if d.rule_id == "phishing.shortened_url")
        assert det.severity.value == "low"
        assert result.verdict is Verdict.SAFE  # one low signal alone stays safe

    def test_lookalike_domain_flagged_high(self):
        result = result_for(caption="verify your account at https://1nstagram-help.net/login")
        assert any(d.rule_id == "phishing.lookalike_domain" for d in result.detections)
        assert result.verdict is not Verdict.SAFE

    def test_messaging_link_without_money_context_is_medium(self):
        result = result_for(caption="join our fan chat https://t.me/fanclub")
        det = next(d for d in result.detections if d.rule_id == "phishing.offplatform_messaging")
        assert det.severity.value == "medium"


class TestDangerousChallenges:
    def test_blackout_challenge(self):
        result = result_for(caption="trying the blackout challenge tonight, who's in?")
        assert any(d.category == "dangerous_challenge" for d in result.detections)
        assert result.verdict is not Verdict.SAFE


class TestSelfHarmAndHarassment:
    def test_kys_comment_forces_unsafe(self):
        result = result_for(comments=["nice video", "kys loser"])
        assert result.verdict is Verdict.UNSAFE
        assert any(d.category == "self_harm" for d in result.detections)

    def test_direct_threat_forces_unsafe(self):
        result = result_for(comments=["i'm going to find you"])
        assert result.verdict is Verdict.UNSAFE


class TestSpam:
    def test_follow_bait_alone_is_low_risk(self):
        result = result_for(caption="follow me to win a prize! f4f")
        assert any(d.category == "spam_engagement_bait" for d in result.detections)

    def test_buy_followers(self):
        result = result_for(hashtags=["freefollowers"], caption="buy followers cheap")
        assert any(d.rule_id == "spam.free_followers" for d in result.detections)


class TestScoring:
    def test_duplicate_rule_same_field_counted_once(self):
        result = result_for(caption="xxx xxx xxx xxx")
        assert result.risk_score == 18  # one MEDIUM adult keyword hit

    def test_score_capped_at_100(self):
        result = result_for(
            caption=(
                "guaranteed profit! free bitcoin giveaway! dm me to invest! "
                "cashapp flip! claim your prize! https://t.me/scam https://bit.ly/x"
            )
        )
        assert result.risk_score <= 100
        assert result.verdict is Verdict.UNSAFE

    def test_detections_sorted_by_severity(self):
        result = result_for(
            caption="follow me to win! guaranteed profit dm me",
        )
        weights = [d.severity for d in result.detections]
        assert weights == sorted(
            weights, key=lambda s: {"low": 0, "medium": 1, "high": 2, "critical": 3}[s.value], reverse=True
        )


class TestReelContent:
    def test_from_dict_roundtrip(self):
        data = {
            "url": "https://www.instagram.com/reel/abc/",
            "caption": "hello",
            "hashtags": ["fun"],
            "comments": ["nice"],
            "author_username": "someone",
            "audio_transcript": "hi there",
        }
        content = ReelContent.from_dict(data)
        assert content.caption == "hello"
        assert len(content.text_fields()) == 4  # caption, transcript, comment, hashtags

    def test_result_to_dict_is_json_shaped(self):
        result = result_for(caption="free bitcoin giveaway")
        d = result.to_dict()
        assert set(d) == {"verdict", "risk_score", "categories", "detections"}
        assert isinstance(d["detections"], list)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
