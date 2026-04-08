import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import os
import hashlib
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse
from xml.etree.ElementTree import Element, SubElement, ElementTree
import xml.etree.ElementTree as ET

BASE_URL = "http://www.kautm.net"
LIST_URL = f"{BASE_URL}/bbs/?so_table=tlo_news&category=recruit"
RSS_FILE = "rss.xml"
STATE_FILE = "state.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}

ALLOWED_QUERY_PARAMS = {"so_table", "mode", "num", "category"}


def normalize_link(raw_link):
    url = urljoin(BASE_URL, raw_link)
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    normalized = {
        "so_table": "tlo_news",
        "mode": "VIEW",
        "category": "recruit",
    }
    if "num" in params:
        normalized["num"] = params["num"]
    query = urlencode(normalized)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))


def make_guid(link):
    parsed = urlparse(link)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    num = params.get("num")
    if num:
        return f"kautm-recruit-{num}"
    return hashlib.md5(link.encode("utf-8")).hexdigest()


def parse_date(date_str):
    date_str = date_str.strip()
    fmt_variants = ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%y-%m-%d")
    for fmt in fmt_variants:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc).strftime(
                "%a, %d %b %Y %H:%M:%S +0000"
            )
        except ValueError:
            continue
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


def fetch_jobs():
    """채용공고 목록 스크래핑"""
    try:
        resp = requests.get(LIST_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except Exception as e:
        print(f"[ERROR] 페이지 요청 실패: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    # tbody 없이 tr 직접 탐색
    rows = soup.select("tr")
    print(f"[DEBUG] 총 tr 개수: {len(rows)}")

    for row in rows:
        a_tag = row.select_one("td.title a")
        if not a_tag:
            continue

        title = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")
        link = BASE_URL + href if href.startswith("/") else href

        tds = row.select("td")
        org = tds[2].get_text(strip=True) if len(tds) > 2 else ""
        date_str = tds[3].get_text(strip=True) if len(tds) > 3 else ""
        deadline_str = tds[5].get_text(strip=True) if len(tds) > 5 else ""

        uid = hashlib.md5(link.encode()).hexdigest()

        jobs.append({
            "uid": uid,
            "title": title,
            "link": link,
            "org": org,
            "date": date_str,
            "deadline": deadline_str,
        })

    return jobs


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"seen_ids": [], "items": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def build_rss(items):
    """RSS 2.0 XML 생성"""
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = "KAUTM 채용공고"
    SubElement(channel, "link").text = LIST_URL
    SubElement(channel, "description").text = "한국산학기술학회 채용공고 RSS 피드"
    SubElement(channel, "language").text = "ko"
    SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    for item in items[:30]:
        entry = SubElement(channel, "item")
        SubElement(entry, "title").text = item["title"]
        SubElement(entry, "link").text = item["link"]
        description = (
            f"기관: {item['org']} / 등록일: {item['date']} / "
            f"마감일: {item['deadline']} / 조회수: {item['views']}"
        )
        SubElement(entry, "description").text = description
        guid_el = SubElement(entry, "guid")
        guid_el.set("isPermaLink", "false")
        guid_el.text = item["uid"]
        SubElement(entry, "pubDate").text = item.get("pub_date")

    tree = ElementTree(rss)
    ET.indent(tree, space="  ")
    with open(RSS_FILE, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)

    print(f"[OK] RSS 저장 완료: {RSS_FILE} ({len(items)}개 항목)")


def main():
    print("[*] 채용공고 스크래핑 시작...")
    jobs = fetch_jobs()
    print(f"[*] {len(jobs)}개 공고 수집")

    state = load_state()
    seen_ids = set(state.get("seen_ids", []))
    existing_items = state.get("items", [])

    new_jobs = []
    for job in jobs:
        if job["uid"] not in seen_ids:
            new_jobs.append(job)
            seen_ids.add(job["uid"])
            print(f"  [NEW] {job['title']}")

    all_items = new_jobs + existing_items
    all_items = all_items[:100]

    build_rss(all_items)

    save_state({"seen_ids": list(seen_ids), "items": all_items})
    print(f"[*] 완료. 신규 공고: {len(new_jobs)}개")


if __name__ == "__main__":
    main()
