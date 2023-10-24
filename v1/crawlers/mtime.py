import datetime
import logging
import time

from .base import BaseCrawler


class MtimeCrawler(BaseCrawler):
    """
    # url = "http://www.mtime.com/top/movie/top100/indx-{}.html"
    # url = 'http://list.mtime.com/listIndex'
    url = "http://front-gateway.mtime.com/library/index/app/topList.api?tt={}&"
    """

    def __init__(self, savedir, overwrite=False, request_option="requests"):
        super(MtimeCrawler, self).__init__(savedir, overwrite)
        self.sitename = "mtime"
        self.baseurl = "http://front-gateway.mtime.com/library/index/app/topList.api"
        self.params = "tt={}"
        self.page_start = 0
        self.page_end = 1
        self.page_interval = 100
        self.total_items = self.page_interval * self.page_end
        self.request_option = request_option
        self.description = "时光电影榜单Top100"
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
        timestamp = int(round(time.time() * 1000))
        url = self.get_url(timestamp)
        logging.info(f"crawl num={self.page_end}, url = {url}")

        page = self.get_page(url)
        if not page:
            return -1, None
        logging.info(f"parse page, page={len(page)}")

        all_list = page["data"]["movieTopList"]["topListInfos"]
        top_list = all_list[0]["items"]
        logging.info(f"save to data, top_list = {len(top_list)}")

        extra = {"more": all_list}
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
            entry = entry["movieInfo"]
            title = entry["movieName"]
            year = entry["releaseDate"][:4]
            score = entry["score"]
            output.append(f"{title} ({year}) ⭐{score}")

        if limit - len(output) > 0:
            output += [""] * (limit - len(output))
        return output
