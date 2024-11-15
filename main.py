from browser import run_browser
import typer
from tool import (
    download_dir,
    find_json,
    load_json,
    dump_json,
    get_output_dir,
    get_output_json,
    get_audio_path,
    check_count,
    check_audio,
)
from callback import get_home_page, get_audio_page
from download import run_download
from rich import print


def main(url, headless: bool = True, output_dir: str = download_dir):
    json_file = find_json(url)
    data = load_json(json_file) if json_file else None
    if data:
        output_dir = get_output_dir(data, url, output_dir)
    else:
        print(f"[bold orange1]get home page:[/] {url}")
        data = run_browser(url, callback=get_home_page, headless=headless)
        output_dir = get_output_dir(data, url, output_dir)
        json_file = get_output_json(output_dir)

        print(f"[bold orange1]success get page:[/] 1/{data['pages_count']} {url}")
        data.update(check_count(output_dir, data))
        dump_json(json_file, data)

    assert len(data["pages"]) == len(
        data["chapters"]
    ), f"数量不相等 pages: {len(data['pages'])} chapters: {len(data['chapters'])}"

    for k, v in enumerate(data["chapters"]):
        if len(v) == 0:
            url = data["pages"][k]
            res = run_browser(url, callback=get_home_page, headless=headless)
            data["chapters"][k] = res["chapters"][0]

            print(
                f"[bold orange1]success get page:[/] {k+1}/{data['pages_count']} {url}"
            )
            data.update(check_count(output_dir, data))
            dump_json(json_file, data)

    count = 0
    for _c in data["chapters"]:
        for chapter in _c:
            count += 1
            if "chapterUrl" in chapter and len(chapter["chapterUrl"]) > 0:
                if not ("audioUrl" in chapter and len(chapter["audioUrl"]) > 0):
                    res = run_browser(
                        chapter["chapterUrl"],
                        callback=get_audio_page,
                        headless=headless,
                        output_dir=output_dir,
                    )
                    if "audioUrl" in res and res["audioUrl"]:
                        chapter["audioUrl"] = res["audioUrl"]
                    print(
                        f"{count}/{data['chapters_count']} [bold green]success get audioUrl[/] {chapter['audioUrl'].split('/')[-1]}"
                    )

                if "audioUrl" in chapter and len(chapter["audioUrl"]) > 0:
                    audio_path = get_audio_path(output_dir, data, chapter)
                    if check_audio(audio_path):
                        print(
                            f"{count}/{data['chapters_count']} [bold green]skip audio[/] {audio_path.name}"
                        )
                        continue

                    run_download(chapter["audioUrl"], audio_path)
                    print(
                        f"{count}/{data['chapters_count']} [bold green]success download audio[/] {audio_path.name}"
                    )

                data.update(check_count(output_dir, data))
                dump_json(json_file, data)

    print(f"title: {data['title']}")


if __name__ == "__main__":
    typer.run(main)
