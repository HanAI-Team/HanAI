from playwright.sync_api import sync_playwright

CAFE_BASE_URL = "https://cafe.daum.net/poordoctor"
USER_DATA_DIR = "./chrome_profile"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,
        args=["--start-maximized"]
    )
    page = context.pages[0]
    page.goto(CAFE_BASE_URL)

    print("로그인 후 Enter를 누르세요...")
    input()

    page.wait_for_timeout(2000)

    # 검색 실행
    iframe0 = page.query_selector_all("iframe")[0]
    frame0 = iframe0.content_frame()
    search_input = frame0.locator("input[name='search_left_query']").first
    search_input.click()
    search_input.fill("혈위")
    search_input.press("Enter")

    # 페이지 이동 완료까지 대기
    page.wait_for_load_state("networkidle", timeout=10000)
    page.wait_for_timeout(3000)
    print(f"\n검색 완료. 현재 URL: {page.url}")

    page.screenshot(path="cafe_search_result.png")

    # iframe#down 확인
    down_iframe = page.query_selector("iframe#down")
    if down_iframe:
        print("iframe#down 발견!")
        frame = down_iframe.content_frame()
        links = frame.query_selector_all("a")
        hrefs = [l.get_attribute("href") or "" for l in links]
        unique = list(dict.fromkeys([h for h in hrefs if h and h != "#"]))
        print(f"링크 수: {len(unique)}")
        # poordoctor 포함 링크
        poor = [h for h in unique if 'poordoctor' in h]
        print(f"\npoordoctor 링크 {len(poor)}개:")
        for h in poor[:10]:
            print(f"  {h}")
        # 그 외 전체 링크 패턴 확인
        print(f"\n전체 링크 (중복제거):")
        for h in unique:
            print(f"  {h}")
    else:
        print("iframe#down 없음")
        # 모든 iframe 확인
        iframes = page.query_selector_all("iframe")
        print(f"총 iframe 수: {len(iframes)}")
        for i, iframe in enumerate(iframes):
            try:
                src = iframe.get_attribute("src") or ""
                frame = iframe.content_frame()
                links = frame.query_selector_all("a")
                hrefs = [l.get_attribute("href") or "" for l in links if l.get_attribute("href")]
                print(f"[iframe #{i}] src={src[:60]} | 링크 {len(hrefs)}개")
                for h in hrefs[:5]:
                    print(f"    {h}")
            except Exception as e:
                print(f"[iframe #{i}] 접근 불가: {e}")

    context.close()
