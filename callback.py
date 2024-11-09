from botasaurus.soupify import soupify
from botasaurus.browser import Wait
from tool import get_domain, get_output_dir, dump_img, get_verify
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


def login(driver, _p, soup, url):
    loginUrl = soup.select_one(".tiquma a")["href"]
    driver.get(get_domain(url) + loginUrl)
    driver.wait_for_element(".verify", wait=Wait.LONG)
    driver.sleep(2)

    username = input("email: ")
    password = input("password: ")
    driver.type("input[name='username']", username)
    driver.type("input[name='password']", password)
    width = 100
    height = 48

    res = driver.run_js(f"""
                        return (()=>{{
                            var el = document.querySelector(".verify")
                            if (el){{
                                var cnv = document.createElement('canvas');
                                cnv.width = {width}; cnv.height = {height};
                                cnv.getContext('2d').drawImage(el, 0, 0);
                                var res = cnv.toDataURL('image/jpeg').substring(22);
                                return res
                            }}
                        }})()
                        """)
    dump_img(_p, res)

    verify = input("verify: ")
    driver.type("input[name='verify']", verify)
    driver.click("button[name='submit']")

    driver.wait_for_element(".top .top-l a", wait=Wait.LONG)
    # driver.sleep(3)
    soup = soupify(driver)
    top = soup.select(".top .top-l a")
    return top[-1].text == "退出登陆"


def get_audio_page(driver, data):
    url = data["url"]
    driver.get(url)
    driver.wait_for_element("#thisbody", wait=Wait.LONG)
    driver.sleep(3)
    soup = soupify(driver)

    audio = soup.select_one("#thisbody audio")
    fix_bug = soup.select_one(".tiquma")
    if "登录继续收听！" in fix_bug.text:
        print("登录继续收听, 建议关闭headless, 然后手动登录")
        _max = 3
        for i in range(_max):
            print(f"login {i+1}/{_max}")
            _p = get_verify(data["output_dir"])
            if login(driver, _p, soup, url):
                print("login success")
                if _p.is_file():
                    _p.unlink()
                return get_audio_page(driver, data)
        raise Exception(f"帐号密码输入错误已超过{_max}次")

    if "访问过快！过段时间再试！" in fix_bug.text:
        # driver.close()
        raise Exception("访问过快！过段时间再试！")

    audioUrl = audio["src"]
    return {"chapterUrl": url, "audioUrl": audioUrl}
