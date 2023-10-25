import logging
from pathlib import Path

import pendulum

from cinephile.crawlers.base import BaseCrawler, CrawlerUrl
from cinephile.utils import datetimes
from cinephile.utils.movies import MovieCluster, Movie


class MaoyanUrl(CrawlerUrl):
    @property
    def key_top100(self):
        return self._key_top100

    @property
    def key_detail(self):
        return self._key_detail

    def url(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        url = config["url"]
        if key == self._key_top100:
            params = config["params"]
            return f"{url}?{params}"
        elif key == self._key_detail:
            movie_id = kwargs["movie_id"]
            return url.format(movie_id)
        return ""

    def source(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        if key == self._key_detail:
            return config["url"].format(kwargs["movie_id"])
        return config["raw_url"]

    def _init_urls(self) -> dict:
        url_dict = {
            self._key_top100: {
                "desc": self.description,
                "url": "https://i.maoyan.com/asgard/asgardapi/mmdb/movieboard/moviedetail/fixedboard/39.json",
                "params": "ci=50&year=0&term=0&limit=100&offset=0",  # ci=50&year=0&term=0&limit=10&offset=20
                "raw_url": [
                    "https://www.maoyan.com/board/4",
                    "https://i.maoyan.com/asgard/board/aggregation"
                ],
                "page_count": 1,
                "total": 100,
                "page_format": "json",
            },
            self._key_detail: {  # todo
                "desc": "猫眼电影详情页",
                "url": "https://www.maoyan.com/films/{}",
                "params": "",
                "total": 1,
            },
        }
        return url_dict


class MaoyanCrawler(BaseCrawler):
    """ 猫眼电影榜单
    """

    def __init__(self, savedir=None, overwrite=False, **kwargs):
        super(MaoyanCrawler, self).__init__(savedir, overwrite)
        self.sitename = "maoyan"
        self.baseurl = "https://www.maoyan.com"
        self.description = "猫眼电影Top100"
        self.urls = MaoyanUrl(self.sitename, self.description)

    def parse_page(self, key, page, char_detect=False, **kwargs):
        if key == self.urls.key_top100:
            return parse_maoyan_json_top(page, **kwargs)
        return None

    def process(self, key=None, savedir=None, **kwargs):
        if key == self.urls.key_top100:
            self.process_top100(savedir)
        elif key == self.urls.key_detail:
            self.process_detail(kwargs["movie_id"], savedir)

    def process_top100(self, savedir=None):
        key = self.urls.key_top100
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        total = url_config["total"]
        savename = self.getname(dt, name=f"{self.save_prefix_top}{total}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, savefile

        headers = self.get_headers()
        url = self.get_url(key)
        page = self.get_page(url, headers, page_format="json")
        if not page:
            logging.warning("page error, exit\n\n")
            return self.error_http, savefile

        draft, movies = self.parse_page(key, page, base_url=self.baseurl)
        if not movies:
            logging.warning("parser error, exit\n\n")
            return self.error_parse, savefile

        logging.info(f"save to data, top movies = {len(movies)}")
        desc = ", ".join([page["data"]["title"], page["data"]["content"]])
        release = pendulum.from_timestamp(int(page["data"]["created"]) / 1000, tz="Asia/Shanghai")
        source = self.get_url(key, is_source=True)
        movie_cluster = MovieCluster(release, dt, desc, source, movies=movies, draft=draft)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_detail(self, movie_id, savedir=None):
        key = self.urls.key_detail


def parse_maoyan_json_top(page, **kwargs):
    base_url = kwargs["base_url"].rstrip("/")
    items = page["data"]["movies"]
    entries = []
    for item in items:
        title = item["nm"]
        rank = item["rank"]
        img = item["img"]
        maoyan_id = item["id"]
        link = f"{base_url}/films/{maoyan_id}"
        year = item["pubDesc"][:4]
        if year.isdigit():
            year = int(year)
        else:
            logging.warning(f"Error year {title}: {year}")
            year = 0
        score = {
            "maoyan-score": item["sc"],
        }
        more = {
            "maoyan-id": maoyan_id,
            "actor": item["star"],
            "date": item["pubDesc"],
            "genre": item["cat"],
            "watch-wish": item["wish"],
            "summary": item["shortDec"],
        }

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
    return items, entries
