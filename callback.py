from botasaurus.soupify import soupify
from botasaurus.browser import Wait
from tool import get_domain
import re


def get_home_page(driver, data):
    """
    https://www.ting13.cc/youshengxiaoshuo/29971
    提取章节目录url
    """
    url = data["url"]
    driver.get(url)
    driver.wait_for_element("h1", wait=Wait.LONG)
    driver.sleep(2)
    soup = soupify(driver)

    domain = get_domain(url)
    title = soup.select_one("h1").text.strip("有声小说")
    playlist = soup.select("#playlist li a")
    chapters = [
        {"chapterUrl": domain + i["href"], "chapterTitle": i.text} for i in playlist
    ]
    _c = soup.select(".hd-sel option")
    _count = re.sub("[\u4e00-\u9fa5]", "", _c[-1].text)
    chapters_count = int(_count.split(" ")[-1])
    pages = [domain + i["value"] for i in _c]
    pages_count = len(pages)

    return {
        "url": url,
        "title": title,
        "chapters_count": chapters_count,
        "check_chapterUrl": False,
        "check_chapterUrl_count": 0,
        "check_audioUrl": False,
        "check_audioUrl_count": 0,
        "check_audioFile": False,
        "check_audioFile_count": 0,
        "check_repeat": False,
        "pages_count": pages_count,
        "pages": pages,
        "chapters": [chapters, *[[] for i in pages][1:]],
    }


def get_audio_page(driver, data):
    url = data["url"]
    driver.get(url)
    driver.wait_for_element("#thisbody", wait=Wait.SHORT)
    driver.sleep(4)
    soup = soupify(driver)

    audio = soup.select_one("#thisbody audio")
    fix_bug = soup.select_one(".tiquma")

    if "登录继续收听！" in fix_bug.text:
        print("登录继续收听, 建议关闭headless, 然后手动登录")
        import pdb

        pdb.set_trace()
        raise Exception("登录后重启即可")

    if "访问过快！过段时间再试！" in fix_bug.text:
        # driver.close()
        raise Exception("访问过快！过段时间再试！")

    audioUrl = audio["src"]
    return {"chapterUrl": url, "audioUrl": audioUrl}
