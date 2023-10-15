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
            return -2
        timestamp = int(round(time.time() * 1000))
        url = self.get_url(timestamp)
        logging.info(f"crawl num={self.page_end}, url = {url}")

        page = self.get_page(url)
        if not page:
            return -1
        logging.info(f"parse page, page={len(page)}")
        all_list = page["data"]["movieTopList"]["topListInfos"]
        top_list = all_list[0]["items"]

        logging.info(f"save to data, top_list = {len(top_list)}")
        extra = {"more": all_list}
        self.save(top_list, **extra)
        return len(top_list)
