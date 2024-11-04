from botasaurus.request import request, Request
from botasaurus.soupify import soupify
from botasaurus.browser import browser, Driver, Wait
from chrome_extension_python import Extension
from botasaurus.lang import Lang
import re
from pathlib import Path
import json
import typer
from pathvalidate import sanitize_filename


download_dir = (Path.home() / "Downloads").as_posix()
g_file_path = ""
callbackObj = None
g_headless = True


def check_audio(file_path):
    return file_path.is_file() and file_path.stat().st_size > 0


def get_domain(url: str):
    return "/".join(url.split("/")[0:3])


@request(output=None)
def run_download(request: Request, url):
    global callbackObj, g_file_path
    if check_audio(g_file_path):
        print(f"skip audio {g_file_path.name}")
        return

    response = request.get(url)
    with open(g_file_path, "wb") as f:
        f.write(response.content)


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
    headless=g_headless,
    reuse_driver=True,
    run_async=True,
    lang=Lang.Chinese,
    add_arguments=["--mute-audio"],
    close_on_crash=True,
    raise_exception=False,
    tiny_profile=True,
    profile="pikachu",
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
    domain = get_domain(url)
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
        "check_chapters_count": 0,
        "check_audios": False,
        "check_audios_count": 0,
        "check_output": False,
        "check_output_count": 0,
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

    for i in range(3):
        driver.sleep(5)
        soup = soupify(driver)
        audio = soup.select("#play audio")[0]
        fix_bug = soup.select(".tiquma")

        if "访问过快！过段时间再试！" in fix_bug[0].text:
            driver.close()
            raise Exception("访问过快！过段时间再试！")

        if "登录继续收听！" in fix_bug[0].text:
            print("登录继续收听, 建议关闭headless, 然后手动登录")
            import pdb

            pdb.set_trace()
            raise Exception("登录后重启即可")

        try:
            audioUrl = audio["src"]
            print(f"audioUrl: {audioUrl.split('/')[-1]}")
            return {"url": url, "audioUrl": audioUrl}
        except KeyError:
            pass
    return {"url": url, "audioUrl": ""}


def callback3(url, soup, driver=None, response=None):
    import pdb

    pdb.set_trace()
    return {}


def switch_browser(url, callback, mode="browser", file_path=""):
    global callbackObj, g_file_path
    callbackObj = callback
    g_file_path = file_path
    if mode == "browser":
        return run_browser(url)
    elif mode == "request":
        return run_request(url)
    elif mode == "download":
        return run_download(url)


def check_count(data, file_path):
    chaptersCount = 0
    audiosCount = 0
    outputCount = 0
    for i in data["data"]:
        for i in i:
            if "chaptersUrl" in i and len(i["chaptersUrl"]) > 0:
                chaptersCount += 1
            if "audioUrl" in i and len(i["audioUrl"]) > 0:
                audiosCount += 1
            try:
                _file_path = get_path(data, i, file_path)
                if check_audio(_file_path):
                    outputCount += 1
            except KeyError:
                pass
    return {
        "check_chapters": chaptersCount == data["chapters_count"],
        "check_audios": audiosCount == data["chapters_count"],
        "check_output": outputCount == data["chapters_count"],
        "check_chapters_count": chaptersCount,
        "check_audios_count": audiosCount,
        "check_output_count": outputCount,
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


def download_audio(audioUrl: str, file_path: str):
    return switch_browser(
        audioUrl, callback=callback3, mode="download", file_path=file_path
    )


def get_name(data, i):
    index = len(str(data["chapters_count"]))
    fill_index = str(i["index"]).zfill(index)
    suffix = i["audioUrl"].split(".")[-1]
    suffix = suffix if suffix else "m4a"
    name = sanitize_filename(f"{fill_index} {i['chaptersTitle']}.{suffix}")
    return name


def get_path(data, i, file_path):
    name = get_name(data, i)
    return file_path.parent / name


def download(i, data, file_path):
    _file_path = get_path(data, i, file_path)
    audioUrl = i["audioUrl"]
    if audioUrl:
        download_audio(audioUrl, file_path=_file_path)
        data.update(check_count(data, file_path=_file_path))
        save_json(file_path, data)


def _download_audio(data, file_path):
    for i in data["data"]:
        for i in i:
            download(i, data, file_path)


def get_audio(data, file_path, mode):
    count = 0
    for i in data["data"]:
        for i in i:
            count += 1
            i["index"] = count

    for i in data["data"]:
        for i in i:
            _file_path = get_path(data, i, file_path)
            if check_audio(_file_path):
                print(f"skip audioUrl and audioFile {_file_path.name}")
                continue

            audioUrl = i["audioUrl"]
            if audioUrl:
                print(f"skip audioUrl2 {get_name(data,i)}")
                print(f"download audio2 {get_name(data,i)}")
                download(i, data, file_path)
                continue

            chaptersUrl = i["chaptersUrl"]
            if chaptersUrl:
                obj = switch_browser(
                    chaptersUrl, callback=callback2, mode=mode, file_path=file_path
                )
                result = obj.get()
                if not result:
                    # raise Exception("error exit app")
                    return
                i["audioUrl"] = result["audioUrl"]

                data.update(check_count(data, file_path=file_path))
                save_json(file_path, data)

                print(
                    f"{i['index']}/{data['chapters_count']} download audio {get_name(data,i)} "
                )
                download(i, data, file_path)


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
    print(f"get  pages {1}/{len(data['pages'])}")

    for k, v in enumerate(data["pages"]):
        if k == 0:
            continue

        if len(data["data"][k]) > 0:
            print(f"skip pages {k+1}/{len(data['pages'])}")
            continue
        print(f"get  pages {k+1}/{len(data['pages'])}")

        obj = switch_browser(v, callback=callback, mode=mode, file_path=file_path)
        _data = obj.get()
        data["data"][k] = [
            {"chaptersUrl": i["url"], "chaptersTitle": i["title"], "audioUrl": ""}
            for i in _data["chapters"]
        ]
        data.update(check_count(data, file_path=file_path))
        save_json(file_path, data)

    get_audio(data=data, file_path=file_path, mode=mode)


if __name__ == "__main__":
    """
    uv run python .\main.py "https://www.ting13.cc/youshengxiaoshuo/12443"
    """
    typer.run(main)
