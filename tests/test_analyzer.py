# -*- coding: utf-8 -*-
import pytest

from reels_safety import analyze, collect_hashtags
from reels_safety.models import Consequence, ReelContent, Severity, Verdict


def result_for(**kwargs):
    return analyze(ReelContent(**kwargs))


class TestCleanContent:
    def test_empty_content_passes(self):
        result = result_for(caption="")
        assert result.verdict is Verdict.PASS
        assert result.risk_score == 0
        assert result.detections == []

    def test_ordinary_creator_caption_passes(self):
        result = result_for(
            caption="今天分享三個讓運鏡更穩的小技巧 🎬 #攝影 #vlog #創作者日常",
            audio_transcript="第一個技巧是把手肘靠在身體上",
        )
        assert result.verdict is Verdict.PASS

    def test_english_clean_caption_passes(self):
        result = result_for(caption="Morning routine that changed my energy levels #morningroutine")
        assert result.verdict is Verdict.PASS


class TestReachRisk:
    def test_engagement_bait_chinese(self):
        result = result_for(caption="按讚+分享+標記3個朋友就抽AirPods！")
        assert any(d.rule_id == "reach.engagement_bait" for d in result.detections)
        assert result.verdict is Verdict.REACH_RISK

    def test_engagement_bait_english(self):
        result = result_for(caption="like and comment to win a free iPhone!")
        assert any(d.rule_id == "reach.engagement_bait" for d in result.detections)

    def test_health_claims_chinese(self):
        result = result_for(caption="7天瘦5公斤，保證有效，無效退費！")
        det = next(d for d in result.detections if d.rule_id == "reach.health_claims")
        assert det.severity is Severity.HIGH
        assert result.verdict is Verdict.REACH_RISK

    def test_repost_watermark_mention(self):
        result = result_for(caption="轉載自抖音，好笑到不行")
        assert any(d.rule_id == "reach.repost_watermark" for d in result.detections)

    def test_clickbait_alone_is_only_review(self):
        result = result_for(caption="震驚！99%的人都不知道這件事")
        assert any(d.rule_id == "reach.clickbait" for d in result.detections)
        assert result.verdict is Verdict.REVIEW  # low severity alone

    def test_follow_bait(self):
        result = result_for(caption="互粉互讚來～ f4f")
        assert any(d.rule_id == "spam.follow_bait" for d in result.detections)
        assert result.verdict is Verdict.REACH_RISK


class TestViolationRisk:
    def test_regulated_goods(self):
        result = result_for(caption="電子煙煙油下單私訊我")
        assert result.verdict is Verdict.VIOLATION_RISK
        assert any(d.consequence is Consequence.REMOVAL for d in result.detections)

    def test_gambling_promo(self):
        result = result_for(caption="娛樂城註冊就送888，連結在主頁")
        assert result.verdict is Verdict.VIOLATION_RISK

    def test_financial_guarantee(self):
        result = result_for(audio_transcript="跟著老師操作保證獲利穩賺不賠")
        assert result.verdict is Verdict.VIOLATION_RISK

    def test_dangerous_challenge(self):
        result = result_for(caption="今天來試 blackout challenge")
        assert result.verdict is Verdict.VIOLATION_RISK

    def test_buy_engagement_is_reach_risk_not_violation(self):
        # MEDIUM removal → 帳號風險警告，但單獨出現不到「違規」級
        result = result_for(caption="有人用過買粉服務嗎")
        assert any(d.rule_id == "spam.buy_engagement" for d in result.detections)
        assert result.verdict is Verdict.REACH_RISK


class TestHashtags:
    def test_hashtags_extracted_from_caption(self):
        content = ReelContent(caption="今天的vlog #日常 #Vlog", hashtags=["旅行"])
        assert sorted(collect_hashtags(content)) == ["vlog", "旅行", "日常"]

    def test_over_hard_limit(self):
        result = result_for(hashtags=[f"tag{i}" for i in range(31)])
        det = next(d for d in result.detections if d.rule_id == "hashtag.over_hard_limit")
        assert det.severity is Severity.HIGH
        assert result.verdict is Verdict.REACH_RISK

    def test_too_many_but_under_limit(self):
        result = result_for(hashtags=[f"tag{i}" for i in range(15)])
        assert any(d.rule_id == "hashtag.too_many" for d in result.detections)
        assert not any(d.rule_id == "hashtag.over_hard_limit" for d in result.detections)

    def test_restricted_hashtag(self):
        result = result_for(caption="new reel! #tagsforlikes #fitness")
        det = next(d for d in result.detections if d.rule_id == "hashtag.restricted")
        assert "#tagsforlikes" in det.evidence
        assert result.verdict is Verdict.REACH_RISK

    def test_duplicate_hashtags(self):
        result = result_for(hashtags=["fitness", "fitness", "gym"])
        assert any(d.rule_id == "hashtag.duplicates" for d in result.detections)

    def test_few_clean_hashtags_pass(self):
        result = result_for(caption="拍攝日記 #攝影 #台北")
        assert result.verdict is Verdict.PASS


class TestDisclosure:
    def test_sponsored_content_flagged_as_quality_note(self):
        result = result_for(caption="這支影片由XX品牌贊助")
        det = next(d for d in result.detections if d.rule_id == "disclosure.paid_partnership")
        assert det.consequence is Consequence.QUALITY
        assert result.verdict is Verdict.REVIEW  # note only, not a risk verdict


class TestScoring:
    def test_duplicate_rule_same_field_counted_once(self):
        result = result_for(caption="互粉 互粉 互粉")
        assert result.risk_score == 18  # one MEDIUM hit

    def test_score_capped_at_100(self):
        result = result_for(
            caption=(
                "娛樂城註冊送888 保證獲利穩賺不賠 電子煙下單私訊 "
                "按讚+分享抽獎 7天瘦5公斤保證有效 互粉 f4f #tagsforlikes"
            )
        )
        assert result.risk_score <= 100
        assert result.verdict is Verdict.VIOLATION_RISK

    def test_detections_sorted_by_severity(self):
        result = result_for(caption="震驚！按讚+分享抽獎 保證獲利穩賺不賠")
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        weights = [order[d.severity.value] for d in result.detections]
        assert weights == sorted(weights, reverse=True)

    def test_quality_notes_do_not_enter_categories(self):
        result = result_for(caption="這支影片由XX品牌贊助")
        assert "disclosure" not in result.categories
        assert result.risk_score > 0  # still shown in score/detections


class TestModels:
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
        result = result_for(caption="按讚+分享就抽獎")
        d = result.to_dict()
        assert set(d) == {"verdict", "risk_score", "categories", "detections"}
        assert d["detections"][0]["suggestion"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
