from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup, NavigableString, Tag


ROOT = Path(__file__).resolve().parent
CORRECTIONS_PATH = ROOT / "corrections.json"
DATA_PATH = ROOT / "data" / "tv_live.json"
WEB_DATA_PATH = ROOT / "web" / "data.js"

BASE_URL = "https://bang-dream.com"
SEARCH_TERM = "バンドリ！TV LIVE"
SEARCH_URL = f"{BASE_URL}/news/?s={quote_plus(SEARCH_TERM)}"
SERIES_START_NEWS_DATE = datetime(2019, 12, 12).date()
JST = timezone(timedelta(hours=9))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 BanGDreamTVStatistic/1.0"
    )
}

EPISODE_RE = re.compile(r"(?:第|[#＃])\s*(\d+)\s*回?")
DATE_RE = re.compile(
    r"(?P<year>20\d{2})年\s*(?P<month>\d{1,2})月\s*(?P<day>\d{1,2})日"
    r"(?:[^\d]{0,20}(?P<hour>\d{1,2})\s*[:：]\s*(?P<minute>\d{2}))?"
)
PAIR_RE = re.compile(
    r"(?P<name>[^\s（）()、,，：:※]+(?:\s+[^\s（）()、,，：:※]+)?)"
    r"\s*[（(](?P<role>[^）)]*?役)\s*[）)]"
)
DESCRIPTOR_RE = re.compile(
    r"(?P<name>[^\s（）()、,，：:※]+(?:\s+[^\s（）()、,，：:※]+)?)"
    r"\s*[（(](?P<description>[^）)]{1,100})\s*[）)]"
)

HEADING_NAMES = {"h1", "h2", "h3", "h4", "h5", "h6"}
APPEARANCE_HEADINGS = {
    "出演": "regular",
    "出演者": "regular",
    "出演キャスト": "regular",
    "キャスト": "regular",
    "MC": "mc",
    "MC出演": "mc",
    "ゲスト": "guest",
    "ゲスト出演": "guest",
    "VTR出演": "vtr",
    "VTRゲスト": "vtr",
    "リモート出演": "remote",
}

IGNORE_NAME_FRAGMENTS = {
    "出演",
    "キャスト",
    "ゲスト",
    "MC",
    "番組",
    "配信",
    "予定",
    "変更",
    "見送り",
    "欠席",
    "体調",
    "都合",
    "お知らせ",
    "メッセージ",
    "アーカイブ",
    "YouTube",
    "役",
    "お願い",
    "理解",
    "了承",
    "につきまして",
    "さん",
    "Part",
}

INVALID_PARSED_NAME_RE = re.compile(r"さん|お願い|理解|了承|につきまして|^Part\d+$")


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class Candidate:
    url: str
    title: str
    news_date: str
    episode: int


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path if parts.path.endswith("/") else f"{parts.path}/"
    return urlunsplit((parts.scheme or "https", parts.netloc, path, "", ""))


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.replace("\u00a0", " ").replace("\u3000", " ")
    return re.sub(r"\s+", " ", value).strip()


def canonical_name(value: str, aliases: dict[str, str] | None = None) -> str:
    name = normalize_text(value)
    name = re.sub(r"\s+", "", name)
    name = name.strip("・,、，。:：")
    return (aliases or {}).get(name, name)


def normalize_role(value: str) -> str:
    role = re.sub(r"\s+", "", normalize_text(value))
    role = re.sub(r"役$", "", role)
    role = re.sub(
        r"^(?:Poppin'Party|Roselia|RAISEASUILEN|MyGO!!!!!(?:Vo\.)?)",
        "",
        role,
        flags=re.IGNORECASE,
    )
    return role.strip()


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def fetch(url: str, attempts: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=HEADERS, timeout=(10, 30))
            response.raise_for_status()
            response.encoding = response.apparent_encoding or response.encoding
            return response.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.6 * (attempt + 1))
    raise UpdateError(f"無法取得 {url}: {last_error}")


def load_corrections() -> dict[str, Any]:
    with CORRECTIONS_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("episode_overrides", {})
    data.setdefault("appearance_overrides", {})
    data.setdefault("person_aliases", {})
    data.setdefault("person_roles", {})
    data.setdefault("person_kinds", {})
    data["episode_overrides"] = {
        canonical_url(url): value for url, value in data["episode_overrides"].items()
    }
    return data


def parse_news_date(text: str) -> datetime.date:
    return datetime.strptime(normalize_text(text), "%Y.%m.%d").date()


def search_page_url(page: int) -> str:
    if page == 1:
        return SEARCH_URL
    return f"{BASE_URL}/news/page/{page}/?s={quote_plus(SEARCH_TERM)}"


def page_count(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    pages = [1]
    for link in soup.select(".wp-pagenavi a[href]"):
        match = re.search(r"/page/(\d+)/", link.get("href", ""))
        if match:
            pages.append(int(match.group(1)))
    return max(pages)


def candidates_from_search_page(
    html: str, corrections: dict[str, Any]
) -> list[Candidate]:
    result: list[Candidate] = []
    soup = BeautifulSoup(html, "html.parser")
    for article in soup.select("article.p-news-list__item"):
        link = article.select_one("a[href]")
        title_node = article.select_one(".p-news-list__item-title")
        date_node = article.select_one(".p-news-list__item-date")
        if not link or not title_node or not date_node:
            continue
        title = normalize_text(title_node.get_text(" ", strip=True))
        url = canonical_url(urljoin(BASE_URL, link.get("href", "")))
        try:
            news_date = parse_news_date(date_node.get_text(strip=True))
        except ValueError:
            continue
        if news_date < SERIES_START_NEWS_DATE or "TV LIVE" not in title:
            continue
        if not any(label in title for label in ("放送のお知らせ", "放送情報", "放送決定")):
            continue
        override = corrections["episode_overrides"].get(url, {})
        match = EPISODE_RE.search(title)
        episode = override.get("episode") or (int(match.group(1)) if match else None)
        if not episode:
            continue
        result.append(
            Candidate(
                url=url,
                title=title,
                news_date=news_date.isoformat(),
                episode=int(episode),
            )
        )
    return result


def discover_candidates(corrections: dict[str, Any]) -> list[Candidate]:
    first_html = fetch(search_page_url(1))
    total_pages = page_count(first_html)
    pages: dict[int, str] = {1: first_html}
    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(fetch, search_page_url(page)): page
                for page in range(2, total_pages + 1)
            }
            for future in as_completed(futures):
                pages[futures[future]] = future.result()

    by_url: dict[str, Candidate] = {}
    for page in sorted(pages):
        for candidate in candidates_from_search_page(pages[page], corrections):
            by_url[candidate.url] = candidate

    candidates = sorted(by_url.values(), key=lambda item: (item.episode, item.url))
    if not candidates:
        raise UpdateError("官方搜尋沒有找到任何 TV LIVE 回次。")
    return candidates


def compact_heading(text: str) -> str:
    return re.sub(r"[\s　]+", "", normalize_text(text)).rstrip("：:")


def section_text(heading: Tag) -> str:
    chunks: list[str] = []
    for node in heading.next_elements:
        if node is heading:
            continue
        if isinstance(node, (Tag, NavigableString)) and heading in getattr(node, "parents", []):
            continue
        if isinstance(node, Tag):
            if node.name in HEADING_NAMES:
                break
            if node.name in {"script", "style", "nav", "footer"}:
                continue
            if node.name == "br":
                chunks.append("\n")
        elif isinstance(node, NavigableString):
            parent = node.parent
            if parent and parent.name not in {"script", "style", "nav", "footer"}:
                chunks.append(str(node))
    text = "".join(chunks).replace("\r", "")
    text = re.sub(r"[\t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_broadcast_at(main: Tag, override: dict[str, Any]) -> str:
    if override.get("broadcast_at"):
        return override["broadcast_at"]

    candidates: list[tuple[int, str]] = []
    for heading in main.find_all(list(HEADING_NAMES)):
        label = compact_heading(heading.get_text(" ", strip=True))
        priority = {"初回放送日": 0, "日時": 1, "放送日時": 2}.get(label)
        if priority is not None:
            candidates.append((priority, section_text(heading)))
    candidates.sort(key=lambda item: item[0])

    for _, text in candidates:
        match = DATE_RE.search(normalize_text(text))
        if not match:
            continue
        hour = int(match.group("hour") or 0)
        minute = int(match.group("minute") or 0)
        value = datetime(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
            hour,
            minute,
            tzinfo=JST,
        )
        return value.isoformat()
    raise UpdateError("找不到播出日期")


def heading_type(label: str) -> str | None:
    compact = compact_heading(label)
    if compact in APPEARANCE_HEADINGS:
        return APPEARANCE_HEADINGS[compact]
    if compact.startswith("VTR") and compact.endswith("出演"):
        return "vtr"
    if compact.startswith("ゲスト") and compact.endswith("出演"):
        return "guest"
    return None


def plausible_unpaired_name(value: str) -> bool:
    value = normalize_text(value).strip("・,、，。:：()（）")
    if not value or len(value) > 36 or re.search(r"https?://|\d{2,}", value):
        return False
    if any(fragment in value for fragment in IGNORE_NAME_FRAGMENTS):
        return False
    if re.search(r"[。！？!?]", value):
        return False
    return bool(re.search(r"[A-Za-zぁ-んァ-ヶ一-龠々]", value))


def parse_people_text(
    text: str,
    appearance_type: str,
    aliases: dict[str, str],
) -> list[dict[str, Any]]:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace(")・", ")、").replace("）・", "）、")
    normalized = re.sub(r"[\t\r]+", " ", normalized)

    people: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw_token in re.split(r"[、,，\n]+", normalized):
        token = normalize_text(raw_token)
        if not token or token.startswith("※"):
            continue
        token_type = appearance_type
        label_match = re.match(
            r"^(出演者?|出演キャスト|キャスト|MC|ゲスト出演?|VTR出演|リモート出演)\s*[:：]\s*",
            token,
        )
        if label_match:
            token_label = compact_heading(label_match.group(1))
            token_type = APPEARANCE_HEADINGS.get(token_label, appearance_type)
            token = token[label_match.end() :].strip()
        matches = list(PAIR_RE.finditer(token))
        for match in matches:
            display_name = normalize_text(match.group("name")).lstrip("・")
            role = normalize_role(match.group("role"))
            name = canonical_name(display_name, aliases)
            if not name:
                continue
            key = (name, token_type)
            if key in seen:
                continue
            seen.add(key)
            people.append(
                {
                    "name": name,
                    "display_name": name,
                    "role": role or None,
                    "description": None,
                    "appearance_type": token_type,
                    "status": "appeared",
                    "raw_listed_text": token,
                }
            )

        remainder = PAIR_RE.sub("", token)
        for match in DESCRIPTOR_RE.finditer(remainder):
            display_name = normalize_text(match.group("name")).lstrip("・")
            description = normalize_text(match.group("description"))
            name = canonical_name(display_name, aliases)
            key = (name, token_type)
            if not name or key in seen:
                continue
            seen.add(key)
            people.append(
                {
                    "name": name,
                    "display_name": name,
                    "role": None,
                    "description": description,
                    "appearance_type": token_type,
                    "status": "appeared",
                    "raw_listed_text": token,
                }
            )
        remainder = DESCRIPTOR_RE.sub("", remainder)
        remainder = re.sub(
            r"^(?:出演者?|出演キャスト|キャスト|MC|ゲスト出演?|VTR出演)\s*[:：]?\s*",
            "",
            remainder,
        ).strip("・ /／")
        for part in [remainder]:
            display_name = normalize_text(part)
            if not plausible_unpaired_name(display_name):
                continue
            name = canonical_name(display_name, aliases)
            key = (name, token_type)
            if not name or key in seen:
                continue
            seen.add(key)
            people.append(
                {
                    "name": name,
                    "display_name": name,
                    "role": None,
                    "description": None,
                    "appearance_type": token_type,
                    "status": "appeared",
                    "raw_listed_text": token,
                }
            )
    return people


def cancelled_names(main_text: str, aliases: dict[str, str]) -> list[str]:
    names: list[str] = []

    group_patterns = [
        re.compile(r"出演予定の(?P<group>[^。]{1,100}?)につきまして"),
        re.compile(r"出演を予定されていました(?P<group>[^。]{1,60}?)につきまして"),
    ]
    for pattern in group_patterns:
        for match in pattern.finditer(main_text):
            tail = main_text[match.end() : match.end() + 140]
            if not re.search(r"出演を見送|出演見送り|欠席|出演キャンセル", tail):
                continue
            for name_match in re.finditer(
                r"([A-Za-zぁ-んァ-ヶ一-龠々・ー]+?)さん", match.group("group")
            ):
                name = canonical_name(name_match.group(1), aliases)
                if name and name not in names:
                    names.append(name)

    patterns = [
        re.compile(
            r"出演予定の\s*([A-Za-zぁ-んァ-ヶ一-龠々・ー]+?)\s*さん.{0,100}?"
            r"(?:出演を見送|出演見送り|欠席|出演キャンセル)",
            re.DOTALL,
        ),
        re.compile(
            r"([A-Za-zぁ-んァ-ヶ一-龠々・ー]+?)\s*さん.{0,80}?"
            r"(?:欠席|出演キャンセル)",
            re.DOTALL,
        ),
    ]
    for pattern in patterns:
        for match in pattern.finditer(main_text):
            name = canonical_name(match.group(1), aliases)
            if name and name not in names:
                names.append(name)
    return names


def find_youtube_url(main: Tag) -> str | None:
    links: list[str] = []
    for link in main.select("a[href]"):
        href = link.get("href", "")
        if "youtu.be/" in href or "youtube.com/live/" in href or "youtube.com/watch" in href:
            links.append(href)
    for href in links:
        if "playlist" not in href and "@bang_dream" not in href:
            return href
    return links[0] if links else None


def apply_appearance_overrides(
    url: str, appearances: list[dict[str, Any]], corrections: dict[str, Any]
) -> list[dict[str, Any]]:
    override = corrections["appearance_overrides"].get(url, {})
    remove_names = {
        canonical_name(name, corrections["person_aliases"])
        for name in override.get("remove", [])
    }
    appearances = [item for item in appearances if item["name"] not in remove_names]
    for item in override.get("add", []):
        display_name = normalize_text(item["name"])
        appearances.append(
            {
                "name": canonical_name(display_name, corrections["person_aliases"]),
                "display_name": canonical_name(
                    display_name, corrections["person_aliases"]
                ),
                "role": item.get("role"),
                "description": item.get("description"),
                "appearance_type": item.get("appearance_type", "regular"),
                "status": item.get("status", "appeared"),
                "raw_listed_text": item.get("note", "人工修正"),
            }
        )
    return appearances


def parse_episode(
    candidate: Candidate, html: str, corrections: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    override = corrections["episode_overrides"].get(candidate.url, {})
    title_node = main.find("h1")
    title = normalize_text(title_node.get_text(" ", strip=True)) if title_node else candidate.title
    try:
        broadcast_at = parse_broadcast_at(main, override)
    except UpdateError as exc:
        raise UpdateError(f"第 {candidate.episode} 回：{exc} ({candidate.url})") from exc

    appearances: list[dict[str, Any]] = []
    seen_headings: set[int] = set()
    for heading in main.find_all(list(HEADING_NAMES)):
        if id(heading) in seen_headings:
            continue
        appearance_type = heading_type(heading.get_text(" ", strip=True))
        if not appearance_type:
            continue
        seen_headings.add(id(heading))
        appearances.extend(
            parse_people_text(
                section_text(heading), appearance_type, corrections["person_aliases"]
            )
        )

    main_text = normalize_text(main.get_text(" ", strip=True))
    canceled = cancelled_names(main_text, corrections["person_aliases"])
    for name in canceled:
        matched = False
        for item in appearances:
            if item["name"] == name:
                item["status"] = "cancelled"
                matched = True
        if not matched:
            appearances.append(
                {
                    "name": name,
                    "display_name": name,
                    "role": None,
                    "description": None,
                    "appearance_type": "regular",
                    "status": "cancelled",
                    "raw_listed_text": "官方公告記載出演見送り／欠席",
                }
            )

    appearances = apply_appearance_overrides(candidate.url, appearances, corrections)
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in appearances:
        key = (item["name"], item["appearance_type"], item["status"])
        unique[key] = item
    appearances = list(unique.values())

    episode = {
        "episode": int(override.get("episode", candidate.episode)),
        "title": title,
        "broadcast_at": broadcast_at,
        "news_date": candidate.news_date,
        "announcement_url": candidate.url,
        "youtube_url": find_youtube_url(main),
        "correction_note": override.get("note"),
    }
    return episode, appearances


def validate_dataset(
    episodes: list[dict[str, Any]], appearances: list[dict[str, Any]]
) -> None:
    if not episodes:
        raise UpdateError("資料集中沒有回次。")
    numbers = [item["episode"] for item in episodes]
    duplicate_numbers = sorted({number for number in numbers if numbers.count(number) > 1})
    if duplicate_numbers:
        raise UpdateError(f"回數重複：{duplicate_numbers}")
    expected = list(range(1, max(numbers) + 1))
    if numbers != expected:
        missing = sorted(set(expected) - set(numbers))
        raise UpdateError(f"回數不連續，缺少：{missing}")

    previous: datetime | None = None
    for episode in episodes:
        try:
            current = datetime.fromisoformat(episode["broadcast_at"])
        except (TypeError, ValueError) as exc:
            raise UpdateError(f"第 {episode['episode']} 回播出日期無效") from exc
        if previous and current < previous:
            raise UpdateError(
                f"播出日期未依回數遞增：第 {episode['episode']} 回 {current.isoformat()}"
            )
        previous = current

    by_episode: dict[int, list[dict[str, Any]]] = {}
    for item in appearances:
        by_episode.setdefault(item["episode"], []).append(item)
        if not item.get("name"):
            raise UpdateError(f"第 {item['episode']} 回有空白姓名")
        if INVALID_PARSED_NAME_RE.search(item["name"]):
            raise UpdateError(
                f"第 {item['episode']} 回疑似將公告文字誤判為姓名：{item['name']}"
            )
    empty = [item["episode"] for item in episodes if not by_episode.get(item["episode"])]
    if empty:
        raise UpdateError(f"以下回次沒有解析到出演者：{empty}")


def build_people(
    appearances: list[dict[str, Any]], corrections: dict[str, Any]
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in appearances:
        person_id = stable_id("person", item["name"])
        item["person_id"] = person_id
        person = grouped.setdefault(
            person_id,
            {
                "id": person_id,
                "name": item["name"],
                "display_name": item["display_name"],
                "kind": "other",
                "roles": [],
                "descriptions": [],
            },
        )
        if item.get("role"):
            role = normalize_role(item["role"])
            role_key = "/".join(sorted(part for part in role.split("/") if part))
            person.setdefault("_role_keys", [])
            if role_key and role_key not in person["_role_keys"]:
                person["roles"].append(role)
                person["_role_keys"].append(role_key)
            person["kind"] = "voice_actor"
        if item.get("description") and item["description"] not in person["descriptions"]:
            person["descriptions"].append(item["description"])

    for person in grouped.values():
        forced_kind = corrections["person_kinds"].get(person["name"])
        if forced_kind:
            person["kind"] = forced_kind
        forced_roles = corrections["person_roles"].get(person["name"])
        if forced_roles:
            person["roles"] = [normalize_role(role) for role in forced_roles]
        person["roles"].sort()
        person["descriptions"].sort()
        person.pop("_role_keys", None)
    return sorted(grouped.values(), key=lambda item: item["name"])


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(content)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write_dataset(dataset: dict[str, Any]) -> None:
    payload = json.dumps(dataset, ensure_ascii=False, indent=2) + "\n"
    browser_payload = "window.TV_LIVE_DATA = " + json.dumps(
        dataset, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"
    atomic_write_text(DATA_PATH, payload)
    atomic_write_text(WEB_DATA_PATH, browser_payload)


def update() -> dict[str, Any]:
    corrections = load_corrections()
    print("搜尋官方 TV LIVE 公告…", flush=True)
    candidates = discover_candidates(corrections)
    print(f"找到 {len(candidates)} 個候選公告，下載各回內容…", flush=True)

    parsed: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch, candidate.url): candidate for candidate in candidates
        }
        completed = 0
        for future in as_completed(futures):
            candidate = futures[future]
            html = future.result()
            parsed.append(parse_episode(candidate, html, corrections))
            completed += 1
            if completed % 50 == 0 or completed == len(candidates):
                print(f"  已解析 {completed}/{len(candidates)} 回", flush=True)

    parsed.sort(key=lambda item: item[0]["episode"])
    episodes = [item[0] for item in parsed]
    appearances: list[dict[str, Any]] = []
    for episode, episode_appearances in parsed:
        for index, appearance in enumerate(episode_appearances, start=1):
            appearance["episode"] = episode["episode"]
            appearance["broadcast_at"] = episode["broadcast_at"]
            appearance["announcement_url"] = episode["announcement_url"]
            appearance["id"] = stable_id(
                "appearance",
                f"{episode['episode']}|{appearance['name']}|"
                f"{appearance['appearance_type']}|{appearance['status']}|{index}",
            )
            appearances.append(appearance)

    validate_dataset(episodes, appearances)
    people = build_people(appearances, corrections)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    dataset = {
        "metadata": {
            "generated_at": now.isoformat(),
            "source": BASE_URL,
            "search_url": SEARCH_URL,
            "series": "BanG Dream! TV LIVE 2020–",
            "timezone": "Asia/Tokyo",
            "latest_episode": episodes[-1]["episode"],
            "episode_count": len(episodes),
            "appearance_count": len(appearances),
            "people_count": len(people),
        },
        "episodes": episodes,
        "appearances": appearances,
        "people": people,
    }
    write_dataset(dataset)
    print(
        f"完成：第 1–{episodes[-1]['episode']} 回、{len(people)} 位人員、"
        f"{len(appearances)} 筆出演紀錄。",
        flush=True,
    )
    return dataset


def main() -> int:
    try:
        update()
    except (UpdateError, requests.RequestException, json.JSONDecodeError) as exc:
        print(f"更新失敗：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
