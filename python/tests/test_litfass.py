from datetime import datetime, timezone

from litfass import FrequencyCap, ad_html, parse_feed, pick_ad

TEXT = {"title": "T <b>", "body": "B", "cta": "Go"}
ADS = parse_feed(
    {
        "version": 1,
        "ads": [
            {"id": "a", "url": "https://t.me/a", "text": {"en": TEXT, "de": {"title": "D", "body": "B", "cta": "Los"}}, "emoji": "📰"},
            {"id": "b", "url": "https://t.me/b", "text": {"en": TEXT}, "placements": ["chat"]},
            {"id": "c", "url": "https://t.me/c", "text": {"en": TEXT}, "end": "2026-01-01"},
            {"id": "bad", "url": "http://x", "text": {"en": TEXT}},
            {"id": "no-en", "url": "https://t.me/y", "text": {"de": TEXT}},
            "junk",
        ],
    }
)
NOW = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_parse_drops_invalid():
    assert [ad.id for ad in ADS] == ["a", "b", "c"]
    assert parse_feed(None) == []


def test_pick_respects_placement_schedule_and_exclude():
    assert pick_ad(ADS, "rewarded", now=NOW).id == "a"
    assert pick_ad(ADS, "chat", now=NOW, exclude=["a"]).id == "b"
    assert pick_ad(ADS, "rewarded", now=NOW, exclude=["a"]).id == "a"
    assert pick_ad([], "chat") is None


def test_localize_and_html():
    assert ADS[0].localize("de-AT").cta == "Los"
    assert ADS[0].localize("fa").cta == "Go"
    html = ad_html(ADS[0], "en")
    assert html.startswith("<i>Anzeige</i>\n📰 <b>T &lt;b&gt;</b>")


def test_frequency_cap():
    now = [0.0]
    cap = FrequencyCap(max_views=2, window=10, clock=lambda: now[0])
    assert cap.record(1) and cap.record(1)
    assert not cap.record(1)
    assert cap.record(2)
    now[0] = 11
    assert cap.remaining(1) == 2


def test_categories_style_and_event_url():
    from litfass import event_url

    ads = parse_feed({"ads": [
        {"id": "n", "url": "https://t.me/n", "text": {"en": TEXT}, "categories": ["news"], "style": {"variant": "poster", "bad": 1}},
        {"id": "g", "url": "https://t.me/g", "text": {"en": TEXT}, "categories": ["gaming"]},
    ]})
    assert ads[0].style == {"variant": "poster"}
    assert pick_ad(ads, "chat", now=NOW, categories=["gaming"]).id == "g"
    assert pick_ad(ads, "chat", now=NOW, categories=["tech"]) is None
    assert event_url("https://x/litfass/v1/feed/abc?x=1") == "https://x/litfass/v1/event/abc"
