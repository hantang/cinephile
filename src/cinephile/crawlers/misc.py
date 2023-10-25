import json
import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup

from cinephile.crawlers.base import BaseCrawler
from cinephile.utils import datetimes
from cinephile.utils.movies import Movie, MovieCluster


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


def parse_imdb_hist_page_month(page, **kwargs):
    soup = BeautifulSoup(page)
    logging.info("Title = {}".format(soup.title.text.strip()))

    div_content = soup.body.find("div", id="content")
    desc = div_content.h1.text.strip()
    table = div_content.find("table", id="calendar-table")
    if not table:
        logging.warning("Error not found calendar-table")
        return None, None
    hrefs = [a["href"] for a in table.find_all("a")]
    logging.info(f"Found hrefs = {len(hrefs)}")
    return desc, hrefs


def parse_imdb_hist_page_date(page, **kwargs):
    soup = BeautifulSoup(page)
    logging.info("Title = {}".format(soup.title.text.strip()))

    div_content = soup.body.find("div", id="content")
    desc = div_content.h1.text.strip()

    sec_main = div_content.find(id="main")
    tables = sec_main.find_all("table", class_="list-data")
    if not tables:
        logging.info("Error")
        return None, None

    table = tables[-1]
    raw_items = table.find_all("tr")
    items = [item for item in raw_items if item.get("class") != ["tr-header"]]
    logging.info(f"items = {len(items)} / {len(raw_items)}")

    entries = []
    for item in items:
        td_list = item.find_all("td")
        rank = td_list[0].text.strip().rstrip(".")
        title = td_list[3].span.a.text.strip()
        year = int(td_list[3].span.span.text.strip("()"))
        score = td_list[2].text.strip()
        count = td_list[4].text.strip().replace(",", "")

        a = td_list[5].find_all("a")[-1]
        link = a["href"]
        extra = a.img["title"]
        extra_out = re.findall(r"position: (\d){1,3} \((\d\.?\d?) with (\d[\d,]+) votes\)", extra)
        img = None
        score = {
            "imdb-score": score,
            "imdb-vote": count,
        }
        more = {
            "imdb_id": link.rstrip("/").split("/")[-1],
        }
        if extra_out:
            more["new-imbd-rank"] = extra_out[0][0]
            more["new-imbd-score"] = extra_out[0][1]
            more["new-imbd-vote"] = extra_out[0][2].replace(",", "")
        movie = Movie(
            title,
            link,
            img,
            year,
            rank=rank,
            mtype=None,
            score=score,
            **more,
        )
        entries.append(movie)
    return desc, entries
