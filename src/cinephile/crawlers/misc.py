import json
import logging
from pathlib import Path

from cinephile.crawlers.base import BaseCrawler
from cinephile.crawlers.misc_parser import parse_imdb_hist_page_date, parse_imdb_hist_page_month
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


if __name__ == "__main__":
    save_dir = "./temp-data"
    crawler = ImdbHistCrawler(save_dir)
    crawler.query_hist(year_month="202301")
    crawler.process_hist_top250(date="20230107")
