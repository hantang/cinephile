import logging
import random
import time

from bs4 import BeautifulSoup

from .base import BaseCrawler
from .base import strip


class DoubanCrawler(BaseCrawler):
    """
    "douban": {
        "url": "https://movie.douban.com/top250?start={}&filter=",
        "params": "",
        "page":{"start": 0, "end": 10, "interval": 25},
        "total": "", "save": "douban-movie-top250"
    },
    """

    def __init__(self, savedir, overwrite=False, request_option="requests"):
        super(DoubanCrawler, self).__init__(savedir, overwrite)
        self.sitename = "douban"
        self.baseurl = "https://movie.douban.com/top250/"
        self.params = "start={}&filter="
        self.page_start = 0
        self.page_end = 10
        self.page_interval = 25
        self.total_items = self.page_interval * self.page_end
        self.request_option = request_option
        self.description = "豆瓣电影Top250"
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
            return response.text

        logging.warning(f"response is null")
        return None

    def parse_page(self, page):
        total = self.page_interval
        # html page
        soup = BeautifulSoup(page, "html.parser")
        grid_view_list = soup.body.find(id="content").find_all("ol", class_="grid_view")
        if len(grid_view_list) == 0:
            logging.warning("grid_view is null")
            return None

        grid_view = grid_view_list[0]
        items = grid_view.find_all("li")
        logging.info(f"items = {len(items)}/{total}")

        entries = []
        info_keys = ["director", "actor", "year", "region", "genre"]
        for item in items:
            rank = item.select_one(".pic em").text
            t1 = item.select_one(".pic img")
            img = t1["src"]
            title = t1["alt"]
            link = item.select_one(".info .hd a")["href"]
            # title2 = [strip(ti.text) for ti in item.select(".info .hd .title")]
            title2 = [
                strip(ti.text) for ti in item.select_one(".info .hd a").find_all("span")
            ]
            info = [v.strip() for v in strip(item.select_one("p").text).split("\n")]
            info_values0 = [
                strip(v) for v in info[0].split("\xa0") if len(strip(v)) > 0
            ]
            info_values1 = [
                strip(v) for v in info[1].split("\xa0") if len(strip(v)) > 0
            ]
            info_values0 += [""] * max(0, 2 - len(info_values0))
            info_values1 += [""] * max(0, 3 - len(info_values1))
            info_values = info_values0 + info_values1

            star = item.select_one(".info .bd .star")
            star_score = star.select_one(".rating_num").text
            star_count = star.find_all("span")[-1].text
            quote = item.select_one(".info .bd .quote")
            quote = quote.text.strip() if quote else ""

            entry = {
                "rank": rank,
                "cover": img,
                "link": link,
                "title": title,
                "title2": title2,
                "info": dict(zip(info_keys, info_values)),
                "star": {"score": star_score, "count": star_count.split("人")[0]},
                "quote": quote,
            }
            entries.append(entry)
        return entries

    def process(self):
        if self.check() and not self.overwrite:
            return -2, None

        top_list = []
        for num in range(self.page_start, self.page_end):
            page_num = num * self.page_interval
            url = self.get_url(None if num == 0 else page_num)
            logging.info(f"crawl num={num+1}/{self.page_end}, url = {url}")

            page = self.get_page(url)
            if num + 1 < self.page_end:
                seconds = random.randint(1, 3)
                logging.info(f"sleep {seconds} seconds")
                time.sleep(seconds)

            if not page:
                continue
            logging.info(f"parse page, page={len(page)}")

            out = self.parse_page(page)
            if out:
                top_list.extend(out)

        logging.info(f"save to data, top_list = {len(top_list)}")
        self.save(top_list)

        output = self.get_output(top_list, self.total_items)
        output = {"desc": self.description, "items": output}
        return len(top_list), output
