from pathlib import Path
import json
from pathvalidate import sanitize_filename
import base64
from imageinterminal import display_image
from time import time, sleep
from urllib.parse import urlparse
from urllib.parse import parse_qs
import shutil

download_dir = Path.home() / "Downloads"

refresh_profile = {"refresh": False, "count": 0}


class safelist(list):
    def get(self, index, default=None):
        try:
            return self[index]
        except IndexError:
            return default


def get_config(json_file="./config.json"):
    try:
        with open(json_file, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {"account": []}


def remove_dir(path):
    if path.is_dir():
        shutil.rmtree(path)


def get_domain(url: str):
    return "/".join(url.split("/")[0:3])


def get_id(url):
    return url.split("?")[0].strip("/").split("/")[-1]


def check_fake_url(url, white_list=[".dnse.top", ".ysxs.top"]):
    flag = False
    for s in white_list:
        if s in url:
            flag = True
    return flag


def find_json(url):
    _id = get_id(url)
    for i in download_dir.glob("*"):
        if i.is_dir() and i.name.split(" ")[-1] == _id:
            for i in i.glob("*"):
                if i.suffix == ".json":
                    return i


def load_json(json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return


def dump_json(json_file, data):
    json_file.parent.mkdir(parents=True, exist_ok=True)
    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def dump_img(path, data):
    with open(path, "wb") as f:
        f.write(base64.b64decode(data))
    display_image(path.as_posix())


def get_verify(path, name="verify.jpg"):
    return path / name


def get_output_dir(data, url, output_dir):
    return Path(output_dir) / f"{data['title']} {get_id(url)}"


def get_output_json(output_dir):
    return output_dir / (output_dir.name + ".json")


def check_audio(file_path, check_size=False):
    new_file_path = file_path.parent / ("!" + file_path.name)
    if check_size:
        return (file_path.is_file() and file_path.stat().st_size > 0) or (
            new_file_path.is_file() and new_file_path.stat().st_size > 0
        )
    else:
        return file_path.is_file() or new_file_path.is_file()


def get_name(data, chapter, idx):
    count_len = len(str(data["chapters_count"]))
    fill_index = str(idx).zfill(count_len)
    suffix = chapter["audioUrl"].split(".")[-1]

    name = sanitize_filename(f"{fill_index} {chapter['chapterTitle']}.{suffix}")
    return name


def get_audio_path(output_dir, data, chapter, idx):
    return output_dir / get_name(data, chapter, idx)


def print_data(data):
    count = f"count: {data['chapters_count']}"
    c_url = f"c_url: {data['check_chapterUrl_count']}"
    a_url = f"a_url: {data['check_audioUrl_count']}"
    a_file = f"a_file: {data['check_audioFile_count']}"
    print(f"{count} {c_url} {a_url} {a_file}")


def check_count(output_dir, data):
    chapterUrlCount = 0
    audioUrlCount = 0
    audioFileCount = 0
    check_repeat = False
    chapterUrl_list = []
    audioUrl_list = []

    for i, _c in enumerate(data["chapters"]):
        count = 48 * i
        for chapter in _c:
            count += 1
            chapter["index"] = count

            if "chapterUrl" in chapter and len(chapter["chapterUrl"]) > 0:
                chapterUrlCount += 1
                if chapter["chapterUrl"] in chapterUrl_list:
                    check_repeat = True
                chapterUrl_list.append(chapter["chapterUrl"])

            if "audioUrl" in chapter and len(chapter["audioUrl"]) > 0:
                audioUrlCount += 1
                if chapter["audioUrl"] in audioUrl_list:
                    check_repeat = True
                audioUrl_list.append(chapter["audioUrl"])

            try:
                audio_path = get_audio_path(output_dir, data, chapter, idx=count)
                if check_audio(audio_path):
                    audioFileCount += 1
            except KeyError:
                pass

    # print_data(data)
    return {
        "check_chapterUrl": chapterUrlCount == data["chapters_count"],
        "check_chapterUrl_count": chapterUrlCount,
        "check_audioUrl": audioUrlCount == data["chapters_count"],
        "check_audioUrl_count": audioUrlCount,
        "check_audioFile": audioFileCount == data["chapters_count"],
        "check_audioFile_count": audioFileCount,
        "check_repeat": check_repeat,
    }


def check_state(driver, timeout=10):
    start = time()
    while 1:
        end = time()
        if end - start > timeout:
            raise TimeoutError(f"TimeoutError {timeout}")
        sleep(0.5)
        # resTitle = driver.run_js("return document.title")
        resState = driver.run_js("return document.readyState")
        # print(end - start, resState)

        if resState == "complete":
            print(f"document complete {end - start}/{timeout}")
            break


def parse_url(url, key_name):
    parsed_url = urlparse(url)
    try:
        return parse_qs(parsed_url.query)[key_name][0]
    except KeyError:
        return None


def get_meta_data(driver):
    return {
        "cookies": driver.get_cookies_dict(),
        "headers": {"User-Agent": driver.user_agent},
    }
