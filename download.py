from tool import check_audio, download_dir
from botasaurus.request import request, Request
from botasaurus_requests.exceptions import ClientException
from pathlib import Path
from rich import print


@request(
    output=None,
    close_on_crash=True,
    raise_exception=True,
)
def request_download(request: Request, data):
    def _(_max=7, retry=1):
        if retry > _max:
            raise RuntimeError(f"已达到最大重试次数{_max} {data['url']}")
        elif retry > 1:
            print(f"[bold yellow]retry download audio[/] {retry}/{_max}")
        else:
            print(
                f"[bold sandy_brown]run download audio[/] {data['url'].split('/')[-1]}"
            )
        file_path = Path(data["file_path"])
        url = data["url"]

        if check_audio(file_path, check_size=data["check_size"]):
            print(f"[bold blue]skip audio[/] {file_path.name}")
            return
        try:
            response = request.get(
                url, cookies=data["cookies"], headers=data["headers"]
            )
        except ClientException as e:
            print(f"[bold red]{e}[/]")
            return _(retry=retry + 1)
        if response.status_code == 404:
            # raise RuntimeError(f"get 404 {url}\n{file_path.name}")
            with open(file_path, "wb") as f:
                print(f"empty file {file_path.name}")
                print(f"get 404 {url}")
                f.write(b"")
                return
        try:
            if "文件或目录中找不到" in response.text:
                with open(file_path, "wb") as f:
                    print(f"empty file {file_path.name}")
                    print(f"get 文件或目录中找不到 {url}")
                    f.write(b"")
                    return
        except UnicodeDecodeError as e:
            with open(file_path, "wb") as f:
                f.write(response.content)

    return _()


def run_download(
    url: str,
    file_path: str,
    cookies: dict,
    headers: dict,
    check_size: bool = False,
):
    request_download(
        {
            "url": url,
            "file_path": file_path,
            "cookies": cookies,
            "headers": headers,
            "check_size": check_size,
        }
    )


if __name__ == "__main__":
    run_download(
        "https://mp3h.ysxs.top/3100a_38a32_3f190_06467_192396/%E7%BD%91%E6%B8%B8%E7%AB%9E%E6%8A%80/%E7%86%9F%E7%9D%A1%E4%B9%8B%E5%90%8E_Onion%E6%B4%8B%E8%91%B1%E5%A4%B420240102/0006.m4a",
        download_dir / "test.m4a",
    )
