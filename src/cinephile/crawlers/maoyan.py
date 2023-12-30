import logging
from pathlib import Path

from cinephile.crawlers.base import BaseCrawler, CrawlerUrl
from cinephile.parsers.maoyan_parser import parse_maoyan_json_top, get_maoyan_params, parse_maoyan_detail
from cinephile.utils import datetimes
from cinephile.utils.movies import MovieCluster


class MaoyanUrl(CrawlerUrl):
    def __init__(self, sitename, description=None):
        self._key_boxoffice = f"{sitename}-boxoffice"
        super().__init__(sitename, description)

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
            return url.format(kwargs["movie_id"])
        return ""

    def source(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        if key == self._key_detail:
            return config["raw_url"].format(kwargs["movie_id"])
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
            self._key_detail: {
                "desc": "猫眼电影详情页",
                "url": "https://www.maoyan.com/ajax/films/{}",
                "raw_url": "https://www.maoyan.com/films/{}",
                "total": 1,
            },
            self._key_boxoffice: {
                "desc": "猫眼电影票房",
                "url": "https://piaofang.maoyan.com/dashboard-ajax/movie",
                "raw_url": "https://piaofang.maoyan.com/"
            }
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
        elif key == self.urls.key_detail:
            return parse_maoyan_detail(page, **kwargs)
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
        desc = self.description
        release = datetimes.timestamp2str(int(page["data"]["created"]), fmt=0)
        source = self.get_url(key, is_source=True)
        movie_cluster = MovieCluster(release, dt, desc, source, movies=movies, draft=draft)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_detail(self, movie_id, savedir=None):
        "猫眼详情页，反爬"
        key = self.urls.key_detail
        dt = datetimes.utcnow()
        movie_id = str(movie_id)
        if "films" in movie_id:
            movie_id = movie_id.strip("/").split("films/")[-1]
        if not movie_id.isdigit():
            logging.warning(f"Error maoyan movie id = {movie_id}")
            return self.error_param, None

        url_config = self.urls.query(key)
        savename = self.getname(dt, name=f"{self.save_prefix_movie}{movie_id}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        params = get_maoyan_params(headers["User-agent"])  # signKey等参数
        url = self.get_url(key, movie_id=movie_id)
        page = self.get_page(url, headers, round_i=1, round_n=1, params=params)
        if not page:
            logging.warning("page error, exit\n\n")
            return self.error_http, None
        logging.info(f"parse page, page={len(page)}")

        movie = self.parse_page(key, page)
        if not movie:
            logging.info("Error not movie")
            return self.error_parse, None
        desc = "{}({})".format(url_config["desc"], movie.title)
        source = self.get_url(key, is_source=True, movie_id=movie_id)
        movie_cluster = MovieCluster(dt, dt, desc, source, movie=movie)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile
