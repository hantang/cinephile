import json
import logging
import random
import time

from .base import BaseCrawler


class DoubanWeeklyCrawler(BaseCrawler):
    """
    实时热门电影（20部）
    https://m.douban.com/subject_collection/movie_real_time_hotest
    实时热门书影音（20个）
    https://m.douban.com/subject_collection/subject_real_time_hotest
    一周口碑电影榜（10部）
    https://m.douban.com/subject_collection/movie_weekly_best

    近期热门电影榜（20部）
    https://m.douban.com/subject_collection/ECPE465QY
    近期高分电影榜（20部）
    https://m.douban.com/subject_collection/EC7Q5H2QI
    近期冷门佳片榜（20部）
    https://m.douban.com/subject_collection/ECSU5CIVQ
    """

    def __init__(self, savedir, overwrite=False, request_option="requests"):
        super(DoubanWeeklyCrawler, self).__init__(savedir, overwrite)
        self.sitename = "douban-weekly"
        self.baseurl = "https://m.douban.com/rexxar/api/v2/subject_collection/{}/items"
        self.params = "start=0&count=50&updated_at=&items_only=1&for_mobile=1"
        self.raw_url = "https://m.douban.com/subject_collection/"
        self.page_start = 0
        self.page_end = 1
        self.page_interval = 20
        self.total_items = self.page_interval * self.page_end
        self.request_option = request_option
        self.desc_info = [
            {"desc": "实时热门电影（20部）", "key": "movie_real_time_hotest"},
            {"desc": "实时热门书影音（20个）", "key": "subject_real_time_hotest"},
            {"desc": "一周口碑电影榜（10部）", "key": "movie_weekly_best"},
            {"desc": "近期热门电影榜（20部）", "key": "ECPE465QY"},
            {"desc": "近期高分电影榜（20部）", "key": "EC7Q5H2QI"},
            {"desc": "近期冷门佳片榜（20部）", "key": "ECSU5CIVQ"},
        ]
        self.headers = {
            "Referer": "https://m.douban.com/",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
        }
        self.description = "豆瓣实时和近期热门"
        self.init_save()

    def get_url(self, key):
        return "{}?{}".format(self.baseurl.format(key), self.params)

    def get_page(self, url):
        response = self.get_page_by_requests(url, headers=self.headers)
        if response:
            return response.json()

        logging.warning(f"response is null")
        return None

    def parse_page(self, page):
        return page["subject_collection_items"]

    def process(self):
        if self.check() and not self.overwrite:
            return -2, None

        top_list = []
        n = len(self.desc_info)
        for i, info in enumerate(self.desc_info):
            desc, key = info["desc"], info["key"]
            url = self.get_url(key)
            logging.info(f"crawl {i+1}/{n} info={info}, url = {url}")
            time.sleep(random.randint(1, 5))

            page = self.get_page(url)
            if not page:
                continue
            logging.info(f"parse page, page={len(page)}")

            out = self.parse_page(page)
            if out:
                entry = {
                    "description": desc,
                    "source": self.raw_url + key,
                    "items": out,
                }
                top_list.append(entry)

        logging.info(f"save to data, top_list = {len(top_list)}")
        self.save(top_list)

        output = self.get_output(top_list, self.total_items)
        output = {"desc": self.description, "items": output}
        return len(top_list), output

    def save(self, top_list, **kwargs):
        data = {
            "datetime": self.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "collects": top_list,
        }

        filename = self.savefile
        logging.info(f"save to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("save done")

    def get_output(self, top_list, limit):
        output = []
        for entry in top_list:
            desc = entry["description"]
            items = entry["items"]
            i = 0
            parts = []
            for item in items:
                i += 1
                rank = item.get("rank")
                if not rank:
                    rank = item.get("rank_value", i)
                rank = int(rank)

                while rank > i:
                    parts.append("")
                    i += 1
                if i > limit:
                    break

                title = item["title"]
                link = item.get("uri")
                if link:
                    title = f"[{title}]({link})"
                year = item.get("year")
                if not year:
                    year = item.get("card_subtitle", "").split("/")[0].strip()
                score = str(item["rating"]["value"]).strip()
                if score in ["0", ""]:
                    score = "🌟--"
                else:
                    score = "⭐{:.2f}".format(float(score))
                type_name = item.get("type_name", "电影")
                img = item["pic"]["normal"]
                text = f"{title}<br/>({year}) {score}"
                text_more = "" if type_name == "电影" else f"<br/>【{type_name}】"
                parts.append([img, text + text_more])
            output.append({"desc": desc, "items": parts})
        return output
