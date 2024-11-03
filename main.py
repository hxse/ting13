from botasaurus.request import request, Request
from botasaurus.soupify import soupify
from botasaurus.browser import browser, Driver, Wait
from chrome_extension_python import Extension
from botasaurus.lang import Lang
import re
from pathlib import Path
import json
import typer

download_dir = (Path.home() / "Downloads").as_posix()

callbackObj = None
headless = True


@request(output=None)
def run_request(request: Request, url):
    global callbackObj
    response = request.get(url)
    soup = soupify(response)
    return callbackObj(url, soup)


@browser(
    extensions=[
        Extension(
            # "https://chromewebstore.google.com/detail/adblock-%E2%80%94-best-ad-blocker/gighmmpiobklfepjocnamgkkbiglidom"
            "https://chromewebstore.google.com/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm"
        )
    ],
    output=None,
    headless=headless,
    reuse_driver=True,
    run_async=True,
    lang=Lang.Chinese,
    add_arguments=["--mute-audio"],
    close_on_crash=True,
)
def run_browser(driver: Driver, url):
    global callbackObj
    driver.get(url)
    soup = soupify(driver)
    return callbackObj(url, soup, driver=driver)


def callback(url, soup, driver=None, response=None):
    """
    https://www.ting13.cc/youshengxiaoshuo/29971
    提取章节目录url
    """
    domain = "/".join(url.split("/")[0:3])
    title = soup.select("h1")[0].text.strip("有声小说")
    playlist = soup.select("#playlist li a")
    chapters = [{"url": domain + i["href"], "title": i.text} for i in playlist]
    _c = soup.select(".hd-sel option")
    _count = re.sub("[\u4e00-\u9fa5]", "", _c[-1].text)
    chapters_count = int(_count.split(" ")[-1])
    pages = [domain + i["value"] for i in _c]
    pages_count = len(pages)

    return {
        "url": url,
        "title": title,
        "chapters_count": chapters_count,
        "check_chapters": False,
        "check_audios": False,
        "pages": pages,
        "pages_count": pages_count,
        "chapters": chapters,
    }


def callback2(url, soup, driver=None, response=None):
    """
    https://www.ting13.cc/play/29971_1_147296.html
    提取音频url
    """

    driver.wait_for_element("#jp_audio_0", wait=Wait.LONG)

    for i in range(5):
        driver.sleep(3)
        soup = soupify(driver)
        audio = soup.select("#play audio")[0]
        fix_bug = soup.select(".tiquma")

        if "访问过快！过段时间再试！" in fix_bug[0].text:
            driver.close()
            raise Exception("访问过快！过段时间再试！")
        try:
            audioUrl = audio["src"]
            return {"url": url, "audioUrl": audioUrl}
        except KeyError:
            pass
    return {"url": url, "audioUrl": ""}


def switch_browser(url, callback, mode="browser"):
    global callbackObj
    callbackObj = callback
    if mode == "browser":
        return run_browser(url)
    else:
        return run_request(url)


def check_count(data):
    chaptersCount = 0
    audiosCount = 0
    for i in data["data"]:
        for i in i:
            if "chaptersUrl" in i and len(i["chaptersUrl"]) > 0:
                chaptersCount += 1
            if "audioUrl" in i and len(i["audioUrl"]) > 0:
                audiosCount += 1
    return {
        "check_chapters": chaptersCount == data["chapters_count"],
        "check_audios": audiosCount == data["chapters_count"],
        "check_chapters_count": chaptersCount,
        "check_audios_count": audiosCount,
    }


def load_json(file_path):
    if file_path.is_file():
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return {}


def save_json(file_path, data):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def get_audio(data, file_path, mode):
    for i in data["data"]:
        for i in i:
            audioUrl = i["audioUrl"]
            if audioUrl:
                print(f"skip {audioUrl.split('/')[-1]}")
                continue
            chaptersUrl = i["chaptersUrl"]
            if chaptersUrl:
                obj = switch_browser(chaptersUrl, callback=callback2, mode=mode)
                result = obj.get()
                if not result:
                    # raise Exception("error exit app")
                    return
                i["audioUrl"] = result["audioUrl"]
                print(result["audioUrl"])

                data.update(check_count(data))
                save_json(file_path, data)


def main(
    url: str,
    mode: str = "browser",
    dirPath: str = download_dir,
):
    obj = switch_browser(url, callback=callback, mode=mode)
    data = obj.get()
    data["data"] = [[] for i in range(data["pages_count"])]
    data["data"][0] = [
        {"chaptersUrl": i["url"], "chaptersTitle": i["title"], "audioUrl": ""}
        for i in data["chapters"]
    ]
    del data["chapters"]

    file_dir = Path(dirPath) / (data["title"] + " " + data["url"].split("/")[4])
    file_path = file_dir / f"{data['title']}.json"

    _d = load_json(file_path)
    data.update(_d)

    for k, v in enumerate(data["pages"]):
        if k == 0:
            continue

        if len(data["data"][k]) > 0:
            print(f"skip pages {k+1}")
            continue

        obj = switch_browser(v, callback=callback, mode=mode)
        _data = obj.get()
        data["data"][k] = [
            {"chaptersUrl": i["url"], "chaptersTitle": i["title"], "audioUrl": ""}
            for i in _data["chapters"]
        ]

        data.update(check_count(data))
        save_json(file_path, data)

    get_audio(data=data, file_path=file_path, mode=mode)


if __name__ == "__main__":
    """
    uv run python .\main.py "https://www.ting13.cc/youshengxiaoshuo/12443"
    """
    typer.run(main)
