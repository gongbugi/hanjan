"""F5 신상 수집 — 소스별 가져오기.

- robots.txt를 지킨다 (401/403이면 전부 금지로 본다)
- 요청 사이에 지연을 둔다
- 사이트 이용약관은 코드가 확인할 수 없다 — roasters.yaml에 넣기 전에 사람이 확인한다
"""

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import yaml
from bs4 import BeautifulSoup
from pydantic import BaseModel

from hanjan.config import Settings


class SourceConfig(BaseModel):
    name: str
    kind: Literal["shopify", "html"]
    url: str
    enabled: bool = True
    # html 전용 CSS 선택자
    item_selector: str | None = None
    title_selector: str | None = None
    link_selector: str | None = None
    text_selector: str | None = None
    price_selector: str | None = None


class SourcesFile(BaseModel):
    sources: list[SourceConfig]


@dataclass(frozen=True)
class RawItem:
    source_name: str
    url: str
    title: str
    text: str
    price: str | None
    available: bool


class RobotsDisallowed(Exception):
    pass


def load_sources(path: str | Path) -> list[SourceConfig]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {"sources": []}
    return SourcesFile.model_validate(data).sources


def html_to_text(html: str) -> str:
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


class Fetcher:
    def __init__(
        self,
        client: httpx.Client,
        user_agent: str,
        delay_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client
        self._ua = user_agent
        self._delay = delay_seconds
        self._sleep = sleep
        self._robots: dict[str, RobotFileParser] = {}
        self._requested = False

    def _throttle(self) -> None:
        if self._requested and self._delay > 0:
            self._sleep(self._delay)
        self._requested = True

    def _robots_for(self, url: str) -> RobotFileParser:
        parts = urlparse(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        parser = self._robots.get(origin)
        if parser is None:
            parser = RobotFileParser()
            self._throttle()
            r = self._client.get(f"{origin}/robots.txt", headers={"User-Agent": self._ua})
            if r.status_code in (401, 403):
                parser.disallow_all = True
            elif r.status_code == 200:
                parser.parse(r.text.splitlines())
            else:
                parser.parse([])  # robots.txt가 없으면 허용
            self._robots[origin] = parser
        return parser

    def get(self, url: str) -> httpx.Response:
        if not self._robots_for(url).can_fetch(self._ua, url):
            raise RobotsDisallowed(f"robots.txt가 막은 주소: {url}")
        self._throttle()
        r = self._client.get(url, headers={"User-Agent": self._ua})
        r.raise_for_status()
        return r


def fetch_shopify(fetcher: Fetcher, src: SourceConfig) -> list[RawItem]:
    base = src.url.rstrip("/")
    products = fetcher.get(f"{base}/products.json?limit=250").json().get("products", [])
    items = []
    for p in products:
        variants = p.get("variants") or []
        items.append(
            RawItem(
                source_name=src.name,
                url=f"{base}/products/{p['handle']}",
                title=(p.get("title") or "").strip(),
                text=html_to_text(p.get("body_html") or ""),
                price=str(variants[0]["price"]) if variants and variants[0].get("price") is not None else None,
                available=any(v.get("available", True) for v in variants) if variants else True,
            )
        )
    return items


def fetch_html(fetcher: Fetcher, src: SourceConfig) -> list[RawItem]:
    if not src.item_selector:
        raise ValueError(f"{src.name}: html 소스에는 item_selector가 필요하다")
    r = fetcher.get(src.url)
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for node in soup.select(src.item_selector):
        title_node = node.select_one(src.title_selector) if src.title_selector else node
        link_node = node.select_one(src.link_selector) if src.link_selector else node.find("a")
        href = link_node.get("href") if link_node else None
        title = title_node.get_text(" ", strip=True) if title_node else ""
        if not href or not title:
            continue
        text_node = node.select_one(src.text_selector) if src.text_selector else node
        price_node = node.select_one(src.price_selector) if src.price_selector else None
        items.append(
            RawItem(
                source_name=src.name,
                url=urljoin(str(r.url), str(href)),
                title=title,
                text=text_node.get_text(" ", strip=True) if text_node else title,
                price=price_node.get_text(strip=True) if price_node else None,
                available=True,
            )
        )
    return items


FETCHERS: dict[str, Callable[[Fetcher, SourceConfig], list[RawItem]]] = {
    "shopify": fetch_shopify,
    "html": fetch_html,
}


@contextmanager
def open_fetcher(settings: Settings) -> Iterator[Fetcher]:
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        yield Fetcher(client, settings.collector_user_agent, settings.collector_delay_seconds)
