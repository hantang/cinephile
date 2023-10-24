import logging
import random
import time

from bs4 import BeautifulSoup

from .base import BaseCrawler
from .base import strip


class TmdbCrawler(BaseCrawler):
    def __init__(self, savedir, overwrite=False, request_option="requests"):
        super(TmdbCrawler, self).__init__(savedir, overwrite)
        self.sitename = "tmdb"
        self.baseurl = "https://www.themoviedb.org/movie/top-rated"
        self.root_url = "https://www.themoviedb.org"
        self.params = "page={}"
        self.params_lang = "language=zh-CN"
        self.page_start = 0
        self.page_end = 15
        self.page_interval = 20
        self.total_items = self.page_interval * self.page_end
        self.total_items2 = 250
        self.request_option = request_option
        self.description = "TMDB高分电影"
        self.init_save()

    def get_url(self, param, lang=False):
        if param:
            url = "{}?{}".format(self.baseurl, self.params.format(param))
            if lang:
                url += "&" + self.params_lang
            return url
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

    def parse_page(self, page, lang=False):
        total = self.page_interval
        soup = BeautifulSoup(page, "html.parser")
        div = soup.body.find("div", class_="page_wrapper")

        items = div.find_all("div", class_="card")
        logging.info(f"items = {len(items)}/{total}")
        entries = []
        for item in items[:total]:
            title = item.h2.text
            if lang:
                entry = {"title": strip(title)}
            else:
                score = item.find("div", class_="user_score_chart")["data-percent"]
                date = item.p.text
                link = item.a["href"].strip()
                img = item.img["src"].strip()
                entry = {
                    "cover": self.root_url + img,
                    "link": self.root_url + link,
                    "title": strip(title),
                    "date": strip(date),
                    "star": {"score": score},
                }
            entries.append(entry)
        return entries

    def process(self):
        if self.check() and not self.overwrite:
            return -2, None

        top_list = []
        rank = 1
        key_lang = self.params_lang.split("=")[-1]
        for num in range(self.page_start, self.page_end):
            url1 = self.get_url(num + 1, lang=False)
            url2 = self.get_url(num + 1, lang=True)
            logging.info(
                f"crawl num={num+1}/{self.page_end}, \n\turl1 = {url1}\n\turl2 = {url2}"
            )
            page1 = self.get_page(url1)
            time.sleep(1)
            page2 = self.get_page(url2)

            if num + 1 < self.page_end:
                seconds = random.randint(1, 3)
                logging.info(f"sleep {seconds} seconds")
                time.sleep(seconds)

            if not (page1 and page2):
                continue
            logging.info(f"parse page, page={len(page1)}, page2={len(page2)}")
            out1 = self.parse_page(page1)
            out2 = self.parse_page(page2)

            out = []
            for e1, e2 in zip(out1, out2):
                e1["rank"] = rank
                e1["titles"] = {key_lang: e2["title"]}
                rank += 1
                out.append(e1)
            if out:
                top_list.extend(out)

        logging.info(f"save to data, top_list = {len(top_list)}")
        self.save(top_list)

        output = self.get_output(top_list, self.total_items2)
        output = {"desc": self.description, "items": output}
        return len(top_list), output

    def get_output(self, top_list, limit):
        output = []
        key_lang = self.params_lang.split("=")[-1]
        i = 0
        for entry in top_list:
            i += 1
            rank = int(entry["rank"])
            while rank > i:
                output.append("")
                i += 1
            if i > limit:
                break
            title = (
                "{} / {}".format(entry["title"], entry["titles"].get(key_lang, ""))
                .strip()
                .strip("/")
            )
            year = entry["date"].split(",")[-1].strip()[:4]
            score = "{:.2f}".format(float(entry["star"]["score"]))
            output.append(f"{title} ({year}) ⭐{score}")
        if limit - len(output) > 0:
            output += [""] * (limit - len(output))
        return output
