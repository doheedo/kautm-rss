import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import os
import hashlib
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


def fetch_jobs():
    try:
        resp = requests.get(LIST_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except Exception as e:
        print(f"[ERROR] 페이지 요청 실패: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # 페이지 받아왔는지 확인
    print(f"[DEBUG] 페이지 길이: {len(resp.text)}")
    print(f"[DEBUG] 봇차단 여부: {'자동등록방지' in resp.text}")

    jobs = []
    # td.title 을 직접 찾아서 부모 tr 탐색
    for title_td in soup.select("td.title"):
        a_tag = title_td.select_one("a")
        if not a_tag:
            continue

        # span.board-subject 에서 제목 추출
        subject = a_tag.select_one("span.board-subject")
        title = subject.get_text(strip=True) if subject else a_tag.get_text(strip=True)

        href = a_tag.get("href", "")
        link = BASE_URL + href if href.startswith("/") else href

        # 부모 tr의 모든 td
        row = title_td.parent
        tds = row.select("td")

        org = tds[2].get_text(strip=True) if len(tds) > 2 else ""
        date_str = tds[3].get_text(strip=True) if len(tds) > 3 else ""
        deadline_str = tds[5].get_text(strip=True) if len(tds) > 5 else ""

        uid = hashlib.md5(link.encode()).hexdigest()

        print(f"[DEBUG] 공고 발견: {title}")
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
        desc = f"기관: {item['org']} | 등록일: {item['date']} | 마감일: {item['deadline']}"
        SubElement(entry, "description").text = desc
        SubElement(entry, "guid", isPermaLink="true").text = item["link"]
        SubElement(entry, "pubDate").text = item.get(
            "pub_date",
            datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
        )

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
            job["pub_date"] = datetime.now(timezone.utc).strftime(
                "%a, %d %b %Y %H:%M:%S +0000"
            )
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
