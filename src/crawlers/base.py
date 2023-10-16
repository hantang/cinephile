import datetime
import json
import logging
from abc import abstractmethod
from pathlib import Path

import requests
from curl_cffi import requests as requests_cffi
from fake_useragent import UserAgent


def strip(text):
    return text.strip().lstrip("/").strip()


def check_encoding(text):
    pass


def get_savename(site, total, dt):
    dt2 = dt.strftime("%Y%m%d")
    savename = f"{site}-movie-top{total}-v{dt2}.json".strip("-")
    return savename


# ABCMeta todo
class BaseCrawler:
    def __init__(self, savedir, overwrite=False):
        self.sitename = ""
        self.baseurl = ""
        self.params = ""
        self.page_start = 0
        self.page_end = 1
        self.page_interval = 1
        self.total_items = 0

        self.http_status_ok = 200
        self.ua = UserAgent()
        self.dt = datetime.datetime.utcnow()
        self.overwrite = overwrite
        self.savedir = savedir
        self.savename = None
        self.savefile = None

    def init_save(self):
        if self.savedir:
            self.savedir = Path(self.savedir)
            if not self.savedir.exists():
                logging.info(f"create savedir = {self.savedir}")
                self.savedir.mkdir(parents=True)

        self.savename = get_savename(self.sitename, self.total_items, self.dt)
        self.savefile = Path(self.savedir, self.savename)
        logging.info(f"savefile = {self.savefile}")

    def get_header(self, agent="random"):
        ua = self.ua
        if agent == "chrome":
            val = ua.chrome
        elif agent == "firefox":
            val = ua.firefox
        elif agent == "edge":
            val = ua.edge
        elif agent == "safari":
            val = ua.safari
        else:
            val = ua.random
        headers = {"User-agent": val}
        return headers

    @abstractmethod
    def get_url(self, param):
        pass

    @abstractmethod
    def get_page(self, url):
        pass

    @abstractmethod
    def parse_page(self, page):
        pass

    @abstractmethod
    def process(self):
        pass

    def check(self):
        filename = self.savefile
        if filename.exists():
            logging.warning(f"save file exists, file={filename}")
            return True
        return False

    def save(self, top_list, **kwargs):
        key_more = "more"
        data = {
            "datetime": self.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": self.baseurl.split("?")[0],
        }
        for k, v in kwargs.items():
            if k != key_more:
                data[k] = v
        if top_list:
            data["movies"] = top_list
        if key_more in kwargs:
            data[key_more] = kwargs[key_more]
        logging.info(f"data keys = {data.keys()}")

        filename = self.savefile
        logging.info(f"save to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("save done")

    def get_page_by_curl_cffi(self, url):
        response = requests_cffi.get(url, impersonate="chrome110")
        if response.status_code != self.http_status_ok:
            logging.warning(f"Error response.status_code = {response.status_code}")
            return None
        return response

    def get_page_by_requests(self, url, headers=None):
        if not headers:
            headers = self.get_header()
        response = requests.get(url, headers=headers)
        if response.status_code != self.http_status_ok:
            logging.warning(f"Error response.status_code = {response.status_code}")
            return None
        return response

    @NotImplementedError
    def get_page_by_selenium(self, url):
        return None

    def get_output(self, top_list, limit):
        output = []
        i = 0
        for entry in top_list:
            i += 1
            rank = int(entry["rank"])
            while rank > i:
                output.append("")
                i += 1
            if i > limit:
                break

            title = entry["title"]
            if isinstance(title, list):
                title = title[0]
            year = str(entry["info"].get("year", ""))[:4]
            score = entry["star"].get("score", "")
            output.append(f"{title} ({year}) ⭐{score}")
        if limit - len(output) > 0:
            output += [""] * (limit - len(output))
        return output
