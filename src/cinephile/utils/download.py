import logging
import random
import time
import traceback

import requests
from fake_useragent import UserAgent

http_status_ok = 200
MY_AGENTS = {
    "macos": {
        "firefox": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/118.0"
        ],
        "chrome": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        ],
        "safari": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Safari/605.1.15",
        ],
    }
}


def _flatten_dict(di):
    out = []
    if isinstance(di, str):
        out.append(di)
    elif isinstance(di, list):
        out.extend(di)
    elif isinstance(di, dict):
        for val in di.values():
            out.extend(_flatten_dict(val))
    return out


def get_ua(option="local"):
    if option in ["random", "firefox", "chrome", "safari"]:
        ua = UserAgent()
        ua_dict = {
            "random": ua.random,
            "firefox": ua.firefox,
            "chrome": ua.chrome,
            "safari": ua.safari,
        }
        val = ua_dict[option]
    else:
        agents = _flatten_dict(MY_AGENTS)
        val = random.choice(agents)
    logging.info(f"option = {option}, \n\tuser-agent = {val}")
    return val


def download_sleep(round_i, sleep_opt, sleep_range=None):
    if sleep_opt == "random":
        a, b = (min(sleep_range), max(sleep_range)) if sleep_range else (1, 5)
        # round bigger，a,b increase
        levels = [31, 67, 101, 139, 173]
        for lvl in levels:
            if round_i < lvl:
                break
            a += lvl % 3
            b += lvl % 3 + lvl % 5

        s = random.randint(a, b)
    elif isinstance(sleep_opt, int) or str(sleep_opt).isdigit():
        s = int(sleep_opt)
    else:
        s = 1
    s = 1  # todo ignore
    logging.info(f"==> sleep = {s}")
    time.sleep(s)


def download_page(url, headers, params, page_format="text", **kwargs):
    assert page_format in ["text", "json"]
    tag = '=' * 50
    round_i, round_n = kwargs.get("round_i", 1), kwargs.get("round_n", 1)
    out, status = None, -1
    info = f"url = {url}" + (f", params = {params}" if params else "")
    logging.info(f"==> round {round_i}/{round_n}, {info}")
    try:
        res = requests.get(url, headers=headers)
        # res = requests.post(url, headers=headers)
    except requests.RequestException:
        logging.error(f"{tag}\n!! Failed url = {url}\n{tag}")
        traceback.print_exc()
        exit(-1)

    if res.status_code == http_status_ok:
        out = res.json() if page_format == "json" else res.text
    else:
        logging.warning(f"{tag}\n! BAD url = {url}, status={res.status_code}\n{tag}")

    return out, status


@NotImplementedError
def download_page_by_curl_cffi(url):
    # response = requests_cffi.get(url, impersonate="chrome110")
    # if response.status_code != http_status_ok:
    #     logging.warning(f"Error response.status_code = {response.status_code}")
    return None


@NotImplementedError
def download_page_by_selenium(url):
    return None
