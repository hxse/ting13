from botasaurus.soupify import soupify
from botasaurus.browser import Wait
from tool import (
    get_domain,
    get_output_dir,
    dump_img,
    get_verify,
    check_state,
    get_meta_data,
    check_fake_url,
    safelist,
)
import re
from rich import print
import random


def get_home_page(driver, data):
    """
    https://www.ting13.cc/youshengxiaoshuo/29971
    提取章节目录url
    """
    url = data["url"]
    driver.get(url, wait=data["waitTime"])
    check_state(driver, timeout=data["timeout"])
    driver.wait_for_element("h1", wait=Wait.LONG)
    soup = soupify(driver)

    domain = get_domain(url)
    title = soup.select_one("h1").text.strip("有声小说")
    playlist = soup.select("#playlist li a")
    chapters = [
        {"chapterUrl": domain + i["href"], "chapterTitle": i.text} for i in playlist
    ]
    assert len(chapters) != 0, f"chapters: {len(chapters)}"
    _c = soup.select(".hd-sel option")
    if not _c:
        chapters_count = len(playlist)
        pages = [url]
        pages_count = 1
    else:
        _count = re.sub("[\u4e00-\u9fa5]", "", _c[-1].text)
        chapters_count = int(_count.split(" ")[-1])
        pages = [domain + i["value"] for i in _c]
        pages_count = len(pages)

    return [
        {
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
        },
        get_meta_data(driver),
    ]


def login(driver, _p, soup, url, waitTime, config):
    loginUrl = soup.select_one("#tiquma .tiquma a")["href"]
    driver.get(get_domain(url) + loginUrl, wait=waitTime)
    driver.wait_for_element(".verify", wait=Wait.LONG)
    driver.sleep(2)

    account = safelist(random.choice(config["account"]))
    default_username = account.get(0, "")
    default_password = account.get(1, "")
    print(f"if empty, use: {default_username}")
    username = input("email: ")
    username = username if username else default_username
    print(f"if empty, use: {default_password}")
    password = input("password: ")
    password = password if password else default_password

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


def switch_source(driver, soup, url, data):
    # driver.click("#tiquma .tiquma-bottom a")
    # driver.sleep(1)
    soup = soupify(driver)
    option = [
        i for i in soup.select(".xialas option") if i.text == data["source"].strip()
    ]
    if len(option) == 0:
        raise RuntimeError(f"换源失败 {data['source']} {url}")
    if "javascript:void(0);" in option[0]["value"]:
        return ""
    newUrl = get_domain(url) + option[0]["value"]
    if newUrl == data["url"]:
        return ""
    return get_domain(url) + option[0]["value"]


def get_audio_page(driver, data, _max=5, retry=1, retry2=1):
    if retry > _max or retry2 > _max:
        raise RuntimeError(f"已达到最大重试次数{_max} {data['url']}")
    elif retry > 1:
        print(f"[bold yellow]retry getAudioUrl[/] {retry}/{_max}")
    elif retry2 > 1:
        print(f"[bold yellow]retry login[/] {retry2}/{_max}")
    else:
        print(f"[bold sandy_brown]run getAudioUrl[/] {data['url'].split('/')[-1]}")

    url = data["url"]
    try:
        driver.get(url, wait=data["waitTime"])
        check_state(driver, timeout=data["timeout"])
    except TimeoutError as e:
        print(f"[bold red]{e}[/]")
        return get_audio_page(driver, data, retry=retry + 1)

    driver.wait_for_element("#thisbody", wait=Wait.LONG)
    driver.sleep(3)
    soup = soupify(driver)
    fix_bug = soup.select_one("#tiquma .tiquma")
    if data["source"]:
        newUrl = switch_source(driver, soup, url, data)
        if newUrl:
            data["url"] = newUrl
            print(f"[bold red]正在尝试换源: {data['source']}[/]")
            return get_audio_page(driver, data, retry2=retry2 + 1)
    if "登录继续收听！" in fix_bug.text:
        print("[bold red]登录继续收听, 建议关闭headless, 然后手动登录[/]")
        _p = get_verify(data["output_dir"])
        if login(driver, _p, soup, url, data["waitTime"], data["config"]):
            print("[bold green]login success[/]")
            if _p.is_file():
                _p.unlink()
            return get_audio_page(driver, data)
        return get_audio_page(driver, data, retry2=retry2 + 1)

    if "访问过快！过段时间再试！" in fix_bug.text:
        raise Exception("访问过快！过段时间再试！")

    try:
        soup = soupify(driver)
        audio = soup.select_one("#thisbody audio")
        audioUrl = audio["src"]
        if not check_fake_url(audioUrl):
            raise RuntimeError(
                f"检测到蜜罐url, 建议更换ip, .ysxs.top not in {audioUrl}"
            )
        return [{"chapterUrl": url, "audioUrl": audioUrl}, get_meta_data(driver)]
    except (KeyError, TypeError) as e:
        print(f"[bold red]{e}[/]")
        return get_audio_page(driver, data, retry=retry + 1)
