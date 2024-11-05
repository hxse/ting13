from pathlib import Path
import json
from pathvalidate import sanitize_filename


def get_domain(url: str):
    return "/".join(url.split("/")[0:3])


download_dir = Path.home() / "Downloads"


def get_id(url):
    return url.split("?")[0].strip("/").split("/")[-1]


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


def get_output_dir(data, url, output_dir):
    return Path(output_dir) / f"{data['title']} {get_id(url)}"


def get_output_json(output_dir):
    return output_dir / (output_dir.name + ".json")


def check_audio(file_path):
    new_file_path = file_path.parent / ("!" + file_path.name)
    return (file_path.is_file() and file_path.stat().st_size > 0) or (
        new_file_path.is_file() and new_file_path.stat().st_size > 0
    )


def get_name(data, chapter):
    index = len(str(data["chapters_count"]))
    fill_index = str(chapter["index"]).zfill(index)
    suffix = (
        chapter["audioUrl"].split(".")[-1]
        if "audioUrl" in chapter and len(chapter["audioUrl"]) > 0
        else "m4a"
    )
    name = sanitize_filename(f"{fill_index} {chapter['chapterTitle']}.{suffix}")
    return name


def get_audio_path(output_dir, data, chapter):
    return output_dir / get_name(data, chapter)


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
    count = 0
    for _c in data["chapters"]:
        for chapter in _c:
            count += 1
            chapter["index"] = count
            if "chapterUrl" in chapter and len(chapter["chapterUrl"]) > 0:
                chapterUrlCount += 1
            if "audioUrl" in chapter and len(chapter["audioUrl"]) > 0:
                audioUrlCount += 1
            try:
                audio_path = get_audio_path(output_dir, data, chapter)
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
    }
