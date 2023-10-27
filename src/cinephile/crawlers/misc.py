import json
import logging
import math
import time
from pathlib import Path

from cinephile.crawlers.base import BaseCrawler
from cinephile.crawlers.misc_parser import parse_imdb_hist_page_date, parse_imdb_hist_page_month
from cinephile.crawlers.misc_parser import parse_listchallenges_page_list, extract_listchallenges_page_info
from cinephile.utils import datetimes
from cinephile.utils.movies import MovieCluster


class ImdbHistCrawler(BaseCrawler):
    """
    month_url: find validate dates
    date_url: from 2014 has all date"s data
    """

    def __init__(self, savedir=None, overwrite=False, **kwargs):
        super().__init__(savedir, overwrite, **kwargs)
        self.sitename = "imdb-hist"
        self.baseurl = "https://250.took.nl/"
        self.description = "IMDb电影Top250"
        self.key_month = f"{self.sitename}-month"
        self.key_date = f"{self.sitename}-date"
        self.url_dict = {
            "date_url": "https://250.took.nl/history/{}/{}/{}/full",
            "month_url": "https://250.took.nl/history/{}/{}",
            "hist_url": "https://250.took.nl/history"
        }

    def process(self, key=None, savedir=None, **kwargs):
        pass

    def save(self, savefile, data, **kwargs):
        filename = Path(savefile)
        if not filename.parent.exists():
            logging.info(f"create dir = {filename.parent}")
            filename.parent.mkdir(parents=True)
        logging.info(f"save to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("save done\n\n")

    def get_url(self, key=None, is_source=False, **kwargs):
        if key == self.key_month:
            year_month = kwargs["year_month"]
            month_url = self.url_dict["month_url"]
            y, m = year_month[:4], int(year_month[-2:])
            url = month_url.format(y, m)
            return url
        elif key == self.key_date:
            date = kwargs["date"]
            date_url = self.url_dict["date_url"]
            y, m, d = date[:4], int(date[6:8]), int(date[-2:])
            url = date_url.format(y, m, d)
            return url

    def parse_page(self, key, page, char_detect=False, **kwargs):
        if key == self.key_month:
            return parse_imdb_hist_page_month(page)
        elif key == self.key_date:
            return parse_imdb_hist_page_date(page)

    def query_hist(self, year_month, savedir=None):
        # year_month = 20XXYY, year=20XX, month=YY
        key = self.key_month
        dt = datetimes.utcnow()
        year_month = str(year_month)[:6]
        assert year_month.isdigit() and len(year_month) == 6

        savename = self.getname(dt, name=f"ym{year_month}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, savefile

        logging.info(f"query hist year-month = {year_month}")
        headers = self.get_headers()
        api_url = self.get_url(key, year_month=year_month)
        page = self.get_page(api_url, headers)
        if not page:
            logging.warning(f"Error get {api_url}")
            return self.error_http, savefile
        desc, links = self.parse_page(key, page)
        logging.info(f"links = {len(links)}")
        data = {
            "sitename": self.sitename,
            "update_time": datetimes.time2str(dt, 1),
            "description": "{}, {}".format(self.description, desc),
            "url": api_url,
            "query": year_month,
            "links": links,
        }
        self.save(savefile, data)
        return len(links), savefile

    def process_hist_top250(self, date, savedir=None):
        # date = 20xxyyzz, year=20xx, month=yy, day=zz
        key = self.key_date
        dt = datetimes.utcnow()
        date = str(date)[:8]
        assert date.isdigit() and len(date) == 8

        savename = self.getname(dt, name=f"dt{date}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, savefile

        logging.info(f"process hist date = {date}")
        headers = self.get_headers()
        api_url = self.get_url(key, date=date)
        page = self.get_page(api_url, headers)
        if not page:
            logging.warning(f"Error get {api_url}")
            return self.error_http, savefile
        head, movies = self.parse_page(key, page)
        if not movies:
            logging.warning("page error, exit")
            return self.error_parse, None

        logging.info(f"result = {len(movies)} ")
        release = head
        desc = "{}, {}".format(self.description, head)
        source = api_url
        movie_cluster = MovieCluster(release, dt, desc, source, movies=movies)
        super().save(savefile, movie_cluster)
        return movie_cluster.total, savefile


class ListChallengesCrawler(BaseCrawler):
    """
    https://www.listchallenges.com/
    https://www.listchallenges.com/1001-movies-2003-2021-chronological
    https://www.listchallenges.com/1001-movies-2003-2021-chronological/list/5
    """

    def __init__(self, savedir=None, overwrite=False, **kwargs):
        super().__init__(savedir, overwrite, **kwargs)
        self.sitename = "list-challenges"
        self.baseurl = "https://www.listchallenges.com/"
        self.description = "List Challenges片单"
        self.key_list = f"{self.sitename}-list"

        self.url_dict = {
            "list_url_base": "https://www.listchallenges.com/{}",
            "list_url_path": "/list/{}",
            "page_step": 40,
        }

    def get_url(self, key=None, is_source=False, **kwargs):
        if key == self.key_list:
            if not is_source and kwargs.get("path"):
                path = kwargs["path"]
                return "{}/{}".format(self.baseurl.rstrip("/"), path.lstrip("/"))

            movie_list_id = kwargs.get("movie_list_id")
            if movie_list_id.startswith("http"):
                url = movie_list_id
            else:
                url = self.url_dict["list_url_base"].format(movie_list_id)
            if is_source:
                return url

            if kwargs.get("page"):
                page = kwargs["page"]
                path = self.url_dict["list_url_path"].format(page)
                return "{}/{}".format(url.rstrip("/"), path.lstrip("/"))
            return url
        return ""

    def parse_page(self, key, page, char_detect=False, **kwargs):
        if key == self.key_list:
            return parse_listchallenges_page_list(page, **kwargs)
        return None

    def process(self, key=None, savedir=None, **kwargs):
        if key == self.key_list:
            self.process_list(kwargs["movie_list_id"], savedir,
                              page_limit=kwargs.get("page_limit", -1), page_start=kwargs.get('page_start', 1))

    def process_list(self, movie_list_id, savedir=None, page_limit=-1, page_start=1):
        key = self.key_list
        dt = datetimes.utcnow()

        movie_list_id_val = movie_list_id.strip("/").split("/")[-1].replace("-", "")
        logging.info(f"movie_list = {movie_list_id_val}")
        postfix = f"p{page_start}" if page_start > 1 else ""
        url_config = self.url_dict
        savename = self.getname(dt, name=f"{self.save_prefix_list}{movie_list_id_val}-{postfix}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        page_step = url_config["page_step"]

        page_num = 1
        page_cnt = -1
        url = self.get_url(key, movie_list_id=movie_list_id)
        page = self.get_page(url, headers, round_i=page_num, round_n=page_cnt)
        if not page:
            logging.warning("page error, exit\n\n")
            return self.error_http, savefile
        more_href, total_num, list_desc = extract_listchallenges_page_info(page)
        # page_cnt = int(math.ceil(total_num / page_step))
        page_cnt = len(more_href)
        logging.info(f"total items = {total_num} page = {page_cnt}")
        out = self.parse_page(key, page, total=page_step, base_url=self.baseurl)
        if not out:
            logging.warning("parse error")
            return self.error_parse, savefile

        if page_start == 1:
            movies = out
        else:
            movies = []
        page_num = max(2, page_start)
        while (page_limit <= 0 or page_num < page_limit) and page_num <= page_cnt:
            if page_num % 10 == 0:
                headers = self.get_headers()
                time.sleep(3)

            url = self.get_url(key, movie_list_id=movie_list_id, path=more_href[page_num - 1])
            page = self.get_page(url, headers, round_i=page_num, round_n=page_cnt, sleep_range=(2, 7))
            if not page:
                break
            logging.info(f"round={page_num}/{page_cnt} parse page, page={len(page)}")
            out = self.parse_page(key, page, total=page_step, base_url=self.baseurl)
            if not out:
                break
            movies.extend(out)
            page_num += 1

        logging.info(f"save to data, top movies = {len(movies)}")
        desc = "\n".join([list_desc[k] for k in ["name", "author", "about"]]) if list_desc else url_config["desc"]
        source = self.get_url(key, movie_list_id=movie_list_id, is_source=True)
        movie_cluster = MovieCluster(dt, dt, desc, source, movies=movies)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile


if __name__ == "__main__":
    save_dir = "./temp-data"
    crawler = ImdbHistCrawler(save_dir)
    crawler.query_hist(year_month="202301")
    crawler.process_hist_top250(date="20230107")
