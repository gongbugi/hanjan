import httpx
import pytest

from hanjan.collect.sources import Fetcher, RobotsDisallowed, SourceConfig, fetch_html, fetch_shopify

SHOPIFY = {
    "products": [
        {
            "title": "에티오피아 구지 워시드",
            "handle": "guji",
            "body_html": "<p>컵노트: <b>레몬</b>, 자스민</p>",
            "variants": [{"price": "18000.00", "available": True}],
        },
        {"title": "드립백 세트", "handle": "dripbag", "body_html": "", "variants": [{"price": "12000", "available": False}]},
    ]
}
HTML_LIST = """
<ul>
  <li class="item"><a href="/p/1"><span class="name">케냐 AA</span></a><p class="desc">블랙커런트</p><em class="price">21,000원</em></li>
  <li class="item"><span class="name">링크 없는 항목</span></li>
</ul>
"""
HTML_SOURCE = SourceConfig(
    name="H",
    kind="html",
    url="https://shop.test/beans",
    item_selector=".item",
    title_selector=".name",
    link_selector="a",
    text_selector=".desc",
    price_selector=".price",
)


def fetcher(routes: dict[str, httpx.Response]):
    sleeps: list[float] = []

    def handler(request: httpx.Request):
        return routes.get(str(request.url), httpx.Response(404))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return Fetcher(client, "hanjan-bot/test", 1.5, sleep=sleeps.append), sleeps


def test_shopify_products_are_parsed_and_requests_are_spaced():
    f, sleeps = fetcher(
        {
            "https://roaster.test/robots.txt": httpx.Response(404),
            "https://roaster.test/products.json?limit=250": httpx.Response(200, json=SHOPIFY),
        }
    )

    items = fetch_shopify(f, SourceConfig(name="R", kind="shopify", url="https://roaster.test/"))

    assert [i.url for i in items] == ["https://roaster.test/products/guji", "https://roaster.test/products/dripbag"]
    assert "레몬" in items[0].text and "<b>" not in items[0].text
    assert items[0].price == "18000.00"
    assert items[1].available is False
    assert sleeps == [1.5]


def test_html_list_uses_selectors_and_resolves_relative_links():
    f, _ = fetcher(
        {
            "https://shop.test/robots.txt": httpx.Response(200, text="User-agent: *\nAllow: /"),
            "https://shop.test/beans": httpx.Response(200, text=HTML_LIST),
        }
    )

    items = fetch_html(f, HTML_SOURCE)

    assert len(items) == 1
    assert (items[0].url, items[0].title, items[0].text, items[0].price) == (
        "https://shop.test/p/1",
        "케냐 AA",
        "블랙커런트",
        "21,000원",
    )


def test_robots_disallow_is_respected():
    f, _ = fetcher({"https://shop.test/robots.txt": httpx.Response(200, text="User-agent: *\nDisallow: /beans")})
    with pytest.raises(RobotsDisallowed):
        fetch_html(f, HTML_SOURCE)


def test_forbidden_robots_means_disallow_all():
    f, _ = fetcher({"https://shop.test/robots.txt": httpx.Response(403)})
    with pytest.raises(RobotsDisallowed):
        fetch_html(f, HTML_SOURCE)
