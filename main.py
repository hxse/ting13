import monkey_patch
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
    parse_url,
)
from callback import get_home_page, get_audio_page
from download import run_download
from rich import print


def main(
    url,
    headless: bool = True,
    output_dir: str = download_dir,
    page: None | int = None,
    c_min: None | int = None,
    c_max: None | int = None,
):
    """
    page: 指定章节页面
    c_min: 当前页面最小章节数, 留空下载当前页面所有章节
    c_max: 当前页面最大章节数, 留空下载当前页面所有章节
    """
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

            p = parse_url(url, "p")
            if p and page is not None:
                if int(p) != int(page):
                    print(f"[bold green]skip specify page {p}[/]")
                    continue

            res = run_browser(url, callback=get_home_page, headless=headless)
            data["chapters"][k] = res["chapters"][0]

            print(
                f"[bold orange1]success get page:[/] {k+1}/{data['pages_count']} {url}"
            )
            data.update(check_count(output_dir, data))
            dump_json(json_file, data)

    for i, _c in enumerate(data["chapters"]):
        count = 48 * i
        for chapter in _c:
            count += 1

            if c_min is not None and c_max is not None:
                if count < c_min or count > c_max:
                    print(f"[bold green]skip specify chapter {count}[/]")
                    continue

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
                    audio_path = get_audio_path(output_dir, data, chapter, idx=count)
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
    app = typer.Typer(pretty_exceptions_show_locals=False)
    app.command()(main)
    app()
