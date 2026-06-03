"""특정 URL 하나를 크롤링해서 기존 CSV에 추가"""
import sys
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

USER_DATA_DIR = "./chrome_profile"
TARGET_URL = sys.argv[1] if len(sys.argv) > 1 else "https://cafe.daum.net/poordoctor/DU1u/417645"
OUTPUT_FILE = sys.argv[2] if len(sys.argv) > 2 else "data/cafe_acupuncture_data.csv"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,
        args=["--start-maximized"]
    )
    page = context.pages[0]
    page.goto("https://cafe.daum.net/poordoctor")

    print("로그인 후 Enter를 누르세요...")
    input()

    print(f"크롤링 중: {TARGET_URL}")
    page.goto(TARGET_URL)
    page.wait_for_timeout(2500)

    iframe_handle = page.query_selector("iframe#down")
    html = iframe_handle.content_frame().content() if iframe_handle else page.content()
    soup = BeautifulSoup(html, 'html.parser')

    title_tag = soup.select_one('span.article_title')
    content_tag = soup.select_one('div#bbs_contents')
    comment_tags = soup.select('div#comment-list span.original_comment')

    row = {
        'url': TARGET_URL,
        'title': title_tag.text.strip() if title_tag else "제목 없음",
        'content': content_tag.text.strip() if content_tag else "",
        'comments': ' | '.join(c.text.strip() for c in comment_tags if c.text.strip()),
    }

    print(f"제목: {row['title']}")
    print(f"본문 길이: {len(row['content'])}자")
    print(f"댓글 수: {len(comment_tags)}개")

    # 기존 CSV에 추가
    try:
        df = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
    except FileNotFoundError:
        df = pd.DataFrame(columns=['url', 'title', 'content', 'comments'])

    if TARGET_URL in df['url'].values:
        print("이미 존재하는 URL — 추가하지 않음")
    else:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"✅ {OUTPUT_FILE}에 추가 완료 (총 {len(df)}건)")

    context.close()
