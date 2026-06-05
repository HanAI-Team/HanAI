import os
import time
from playwright.sync_api import sync_playwright
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup

CAFE_BASE_URL = "https://cafe.daum.net/poordoctor"
USER_DATA_DIR = "./chrome_profile"

# 크롤링할 게시판 목록 (이미 완료된 3A4R 제외)
BOARDS = [
    {"id": "39y2", "name": "게시판39y2",  "end_page": 70, "output": "cafe_39y2_final_data.csv"},
    {"id": "39y7", "name": "새게시판",    "end_page": 70, "output": "cafe_new_board_data.csv"},
    {"id": "ADvi", "name": "임상자료실",  "end_page": 30, "output": "cafe_ADvi_data.csv"},
    {"id": "39y3", "name": "강의자료",    "end_page": 70, "output": "cafe_39y3_lecture_data.csv"},
]


def collect_urls(page, board_id, end_page):
    """게시판에서 글 URL 목록 수집"""
    board_url = f"{CAFE_BASE_URL}/{board_id}"
    page.goto(board_url)
    page.wait_for_timeout(2000)

    post_urls = []

    for page_num in range(1, end_page + 1):
        print(f"   📦 {page_num}/{end_page} 페이지 링크 수집 중...")

        try:
            iframe_handle = page.query_selector("iframe#down")
            frame = iframe_handle.content_frame()

            if page_num > 1:
                frame.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                page.wait_for_timeout(1000)

                target_button = frame.locator(f"//ol[@class='list_paging']//span[@class='num_item' and text()='{page_num}']")
                if target_button.count() == 0:
                    target_button = frame.locator(f"xpath=//a[./span[text()='{page_num}']]")

                if target_button.count() > 0:
                    target_button.first.click()
                    page.wait_for_timeout(2500)
                else:
                    print(f"   ⏹️ {page_num}페이지 버튼 없음 → 링크 수집 종료")
                    break

            html = frame.content()
            soup = BeautifulSoup(html, 'html.parser')

            page_links_count = 0
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if ('bbs_read' in href or 'article-id' in href) and link.text.strip():
                    if not href.startswith('http'):
                        href = "https://cafe.daum.net" + href
                    if href not in post_urls:
                        post_urls.append(href)
                        page_links_count += 1

            print(f"      → 새 링크 {page_links_count}개 (누적 {len(post_urls)}개)")

            if page_links_count == 0 and page_num > 5:
                print("   ⏹️ 더 이상 글 없음 → 종료")
                break

        except Exception as e:
            print(f"   ⚠️ {page_num}페이지 에러: {e}")
            continue

        time.sleep(1)

    return post_urls


def collect_contents(page, post_urls, board_id, output_file):
    """URL 목록에서 본문 + 댓글 수집"""
    dataset = []

    for i, url in enumerate(tqdm(post_urls, desc="본문 수집")):
        try:
            page.goto(url)
            page.wait_for_timeout(2500)

            iframe_handle = page.query_selector("iframe#down")
            html = iframe_handle.content_frame().content() if iframe_handle else page.content()
            soup = BeautifulSoup(html, 'html.parser')

            title_tag = soup.select_one('span.article_title')
            content_tag = soup.select_one('div#bbs_contents')
            comment_tags = soup.select('div#comment-list span.original_comment')

            dataset.append({
                'url': url,
                'title': title_tag.text.strip() if title_tag else "제목 없음",
                'content': content_tag.text.strip() if content_tag else "",
                'comments': ' | '.join(c.text.strip() for c in comment_tags if c.text.strip()),
            })

            if (i + 1) % 100 == 0:
                pd.DataFrame(dataset).to_csv(
                    f'cafe_checkpoint_{board_id}_{i+1}.csv', index=False, encoding='utf-8-sig'
                )

        except Exception as e:
            print(f"\n❌ 에러 ({url}): {e}")
            continue

    df = pd.DataFrame(dataset)
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ {output_file} 저장 완료 ({len(df)}건)")


def run_crawler():
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--start-maximized"]
        )

        page = context.pages[0]
        page.goto(CAFE_BASE_URL)

        print("🔒 브라우저에서 카카오 로그인 후 Enter를 누르세요...")
        input()

        for board in BOARDS:
            print(f"\n{'='*50}")
            print(f"📋 [{board['name']}] 게시판 크롤링 시작 (board id: {board['id']})")
            print(f"{'='*50}")

            print("🔗 1단계: URL 수집")
            post_urls = collect_urls(page, board['id'], board['end_page'])
            print(f"✅ 총 {len(post_urls)}개 URL 확보\n")

            if not post_urls:
                print("❌ 수집된 URL 없음 → 다음 게시판으로")
                continue

            print("📝 2단계: 본문 + 댓글 수집")
            collect_contents(page, post_urls, board['id'], board['output'])

        print("\n🎉 전체 게시판 크롤링 완료!")
        context.close()


def collect_search_urls(page, keyword, end_page):
    """카페 검색창에 키워드 입력 후 결과 페이지에서 URL 수집"""
    post_urls = []

    # 1. 카페 홈에서 검색창 찾아 키워드 입력
    print(f"   🔍 '{keyword}' 검색 중...")
    page.goto(CAFE_BASE_URL)
    page.wait_for_timeout(2000)

    try:
        # 검색창은 iframe #0 안에 있음
        iframe_handle = page.query_selector_all("iframe")[0]
        frame = iframe_handle.content_frame()
        search_input = frame.locator("input[name='search_left_query']").first
        search_input.click()
        search_input.fill(keyword)
        search_input.press("Enter")
        page.wait_for_timeout(3000)
        print("   ✅ 검색 완료")
    except Exception as e:
        print(f"   ⚠️ 검색창 입력 실패: {e}")
        return post_urls

    # 2. 검색 결과 페이지마다 링크 수집
    for page_num in range(1, end_page + 1):
        print(f"   📦 {page_num}/{end_page} 페이지 링크 수집 중...")

        try:
            iframe_handle = page.query_selector("iframe#down")
            if not iframe_handle:
                html = page.content()
                frame = None
            else:
                frame = iframe_handle.content_frame()
                html = frame.content()

            soup = BeautifulSoup(html, 'html.parser')

            page_links_count = 0
            for link in soup.find_all('a'):
                href = link.get('href', '')
                # 검색 결과는 bbs_nsread 형식 사용
                if 'bbs_nsread' in href and 'datanum' in href:
                    if not href.startswith('http'):
                        href = "https://cafe.daum.net" + href
                    if href not in post_urls:
                        post_urls.append(href)
                        page_links_count += 1

            print(f"      → 새 링크 {page_links_count}개 (누적 {len(post_urls)}개)")

            if page_links_count == 0:
                print(f"   ⏹️ {page_num}페이지 결과 없음 → 종료")
                break

            # 다음 페이지: goPage() 함수 호출
            if page_num < end_page:
                try:
                    if frame:
                        frame.evaluate(f"goPage({page_num + 1})")
                    else:
                        page.evaluate(f"goPage({page_num + 1})")
                    page.wait_for_timeout(2500)
                except Exception as e:
                    print(f"   ⚠️ 페이지 이동 실패: {e}")
                    break

        except Exception as e:
            print(f"   ⚠️ {page_num}페이지 에러: {e}")
            continue

        time.sleep(1)

    return post_urls


def run_search_crawler(keyword="혈위", end_page=38, output="cafe_acupuncture_data.csv"):
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--start-maximized"]
        )

        page = context.pages[0]
        page.goto(CAFE_BASE_URL)

        print("🔒 브라우저에서 카카오 로그인 후 Enter를 누르세요...")
        input()

        print(f"\n🔍 '{keyword}' 검색 결과 크롤링 시작 (최대 {end_page}페이지)")
        post_urls = collect_search_urls(page, keyword, end_page)
        print(f"✅ 총 {len(post_urls)}개 URL 확보\n")

        if post_urls:
            print("📝 본문 + 댓글 수집")
            collect_contents(page, post_urls, "search", output)

        print("\n🎉 검색 크롤링 완료!")
        context.close()


if __name__ == "__main__":
    import sys
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        keyword = sys.argv[2] if len(sys.argv) > 2 else "혈위"
        end_page = int(sys.argv[3]) if len(sys.argv) > 3 else 38
        safe_name = keyword.replace(" ", "_")
        output = os.path.join(DATA_DIR, f"cafe_{safe_name}_data.csv")
        run_search_crawler(keyword=keyword, end_page=end_page, output=output)
    else:
        run_crawler()
