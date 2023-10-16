import datetime
import logging
import random
import time

from bs4 import BeautifulSoup

from .base import BaseCrawler


@DeprecationWarning
def get_url(offset, headers):
    url_base = "https://www.maoyan.com/board/4"
    parts = {
        "method": "GET",
        "timeStamp": str(int(time.time() * 1000)),
        "User-Agent": headers["User-agent"],
        "index": random.randint(1, 10),
        "channelId": 40011,
        "sVersion": 1,
        "signKey": None,
        "webdriver": "webdriver",
        "offset": offset,
    }

    # keys1 = ["method", "timeStamp", "User-Agent", "index", "channelId", "sVersion"]
    # keys2 = ["timeStamp", "channelId", "index", "signKey", "sVersion", "webdriver"]
    # if offset > 0:
    #     keys2 += ["offset"]
    # c = "&".join([f"{k}={parts[k]}" for k in keys1])
    # u= '&key=A013F70DB97834C0A5492378BD76C53A'
    # parts['signKey']=hashlib.md5((c+u).encode("utf-8")).hexdigest()
    # params = "&".join([f"{k}={parts[k]}" for k in keys2])
    # url = f"{url_base}?{params}"
    url = url_base
    if offset > 0:
        url += f"?offset={offset}"
    return url


@DeprecationWarning
def parse_v1(text):
    base = "https://www.maoyan.com"
    soup = BeautifulSoup(text, "html.parser")
    page_title = soup.title.text
    if page_title == "猫眼验证中心":
        print(page_title)
        return None, None

    nfb = soup.find("div", class_="not-found-body")
    if nfb:
        print(nfb.text.strip())
        return None, None

    divMain = soup.body.find("div", class_="main")
    updateTime = divMain.find("p", class_="update-time").text
    items = divMain.dl.find_all("dd")
    entries = []

    for item in items:
        rank = item.i.text
        img = item.find("img", class_="board-img")
        img = img["src"] if img.get("src") else img["data-src"]
        info = item.find("div", class_="movie-item-info")
        name = info.find("p", class_="name")
        link = base + name.a["href"]
        title = name.text
        actor = info.find("p", class_="star").text.strip()

        date = info.find("p", class_="releasetime").text.strip()
        parts = date.split("：")[1].split("(")
        year = parts[0].split("-")[0]
        region = parts[1].rstrip(")") if len(parts) > 1 else ""
        score = item.find("div", class_="movie-item-number").text.strip()
        entry = {
            "rank": rank,
            "cover": img,
            "link": link,
            "title": [title],
            "info": {"actor": actor, "year": year, "date": date, "region": region},
            "star": {"score": score},
        }
        entries.append(entry)
    return entries, updateTime


class MaoyanCrawler(BaseCrawler):
    """
    - desktop: https://www.maoyan.com/board/4
    - mobile: https://i.maoyan.com/asgard/board/aggregation
    - api: https://i.maoyan.com/asgard/asgardapi/mmdb/movieboard/moviedetail/fixedboard/39.json?ci=1&year=0&term=0&limit=100&offset=0
    """

    def __init__(self, savedir, overwrite=False, request_option="requests"):
        super(MaoyanCrawler, self).__init__(savedir, overwrite)
        self.sitename = "maoyan"
        self.baseurl = "https://i.maoyan.com/asgard/asgardapi/mmdb/movieboard/moviedetail/fixedboard/39.json"
        # self.params = "ci=1&year=0&term=0&limit=100"
        self.params = "ci=1&year=0&term=0&limit={}&offset=0"
        self.page_start = 0
        self.page_end = 1
        self.page_interval = 100
        self.total_items = self.page_interval * self.page_end
        self.request_option = request_option
        self.description = "猫眼电影Top100"
        self.init_save()

    def get_url(self, param):
        if param:
            return "{}?{}".format(self.baseurl, self.params.format(param))
        return self.baseurl

    def get_page(self, url):
        if self.request_option == "requests":
            response = self.get_page_by_requests(url)
        else:
            response = self.get_page_by_curl_cffi(url)

        if response:
            return response.json()

        logging.warning(f"response is null")
        return None

    def parse_page(self, page):
        updateTime = datetime.datetime.fromtimestamp(
            int(page["data"]["created"]) // 1000
        )
        updateTime = updateTime.strftime("%Y-%m-%d")
        entries = page["data"]["movies"]

        return entries, updateTime

    def process(self):
        if self.check() and not self.overwrite:
            return -2, None
        url = self.get_url(self.total_items)
        logging.info(f"crawl num={self.page_end}, url = {url}")

        page = self.get_page(url)
        if not page:
            return -1, None
        logging.info(f"parse page, page={len(page)}")

        top_list, updateTime = self.parse_page(page)
        logging.info(f"save to data, top_list = {len(top_list)}")

        extra = {"update": updateTime}
        self.save(top_list, **extra)

        output = self.get_output(top_list, self.total_items)
        output = {"desc": self.description, "items": output}
        return len(top_list), output

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

            title = entry["nm"]
            year = entry["pubDesc"][:4]
            score = entry["sc"]
            output.append(f"{title} ({year}) ⭐{score}")

        if limit - len(output) > 0:
            output += [""] * (limit - len(output))
        return output
