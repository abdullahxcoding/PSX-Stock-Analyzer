from datetime import datetime
from pathlib import Path

from app.scrapers.news_feeds import _parse_rss, tag_to_companies

FIXTURES = Path(__file__).parent / "fixtures"

COMPANIES = [
    {"ticker": "LUCK", "name": "Lucky Cement Limited"},
    {"ticker": "OGDC", "name": "Oil & Gas Development Company Limited"},
    {"ticker": "FFC", "name": "Fauji Fertilizer Company Limited"},
]


def _tagged_items():
    xml_text = (FIXTURES / "rss_feed_sample.xml").read_text(encoding="utf-8")
    items = _parse_rss(xml_text)
    for item in items:
        item["feed_name"] = "business_recorder_business"
    return items


def test_parses_rss_items():
    items = _tagged_items()
    assert len(items) == 4
    assert items[0]["title"] == "Lucky Cement announces expansion plans for new plant"
    assert items[0]["link"] == "https://www.brecorder.com/news/40000001/lucky-cement-expansion"
    assert items[0]["published_at"] is not None


def test_tags_article_by_company_name_match():
    items = _tagged_items()
    rows = tag_to_companies(items, COMPANIES)
    luck_rows = [r for r in rows if r["ticker"] == "LUCK"]
    assert len(luck_rows) == 1
    assert luck_rows[0]["source_type"] == "general_news"
    assert luck_rows[0]["category"] == "business_recorder_business"
    assert luck_rows[0]["source"] == "business_recorder"


def test_tags_article_by_ticker_word_match():
    items = _tagged_items()
    rows = tag_to_companies(items, COMPANIES)
    ogdc_rows = [r for r in rows if r["ticker"] == "OGDC"]
    assert len(ogdc_rows) == 1
    assert "OGDC" in ogdc_rows[0]["title"]


def test_unrelated_articles_and_unrelated_companies_dont_match():
    items = _tagged_items()
    rows = tag_to_companies(items, COMPANIES)
    # FFC never appears anywhere in the fixture -> no rows for it.
    assert not any(r["ticker"] == "FFC" for r in rows)
    # The gold-price and SBP articles shouldn't match any of the 3 companies.
    matched_titles = {r["title"] for r in rows}
    assert "Gold prices nosedive amid global uncertainty" not in matched_titles
    assert "SBP holds policy rate steady at 11%" not in matched_titles


def test_known_limitation_formal_name_may_not_match_casual_mention():
    # Documents the known limitation: an article referring to OGDC only by
    # its formal registered name in an unusual way won't match if the
    # phrasing differs from the exact stored name. Ticker matching is the
    # reliable path for such companies; name matching is a bonus, not a
    # guarantee, for companies whose common usage name differs from the
    # register name.
    items = [
        {
            "title": "Oil and gas major posts record profit",  # no ticker, informal name
            "link": "https://example.com/1",
            "description": "",
            "published_at": datetime(2026, 8, 30, 10, 0, 0),
            "feed_name": "business_recorder_business",
        }
    ]
    rows = tag_to_companies(items, COMPANIES)
    assert not any(r["ticker"] == "OGDC" for r in rows)
