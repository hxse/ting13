from botasaurus.soupify import soupify
from botasaurus.browser import browser, Driver, Wait


def get_profile(data):
    print(data)
    return data["profile"]


@browser(headless=False, profile=get_profile)
def run_browser(driver: Driver, url):
    print(url)
    driver.get("https://www.google.com")
    soup = soupify(driver)
    title = soup.select_one("title")
    print(title)
    driver.prompt()


if __name__ == "__main__":
    run_browser(
        # "https://www.google.com",
        [
            {"profile": "pikachu"},
            {"profile": "pikachu2"},
        ],
    )
