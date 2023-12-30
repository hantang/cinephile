import logging
import math
from pathlib import Path

from cinephile.crawlers.base import BaseCrawler, CrawlerUrl
from cinephile.parsers.tmdb_parser import parse_tmdb_page_detail, parse_tmdb_page_top, parse_tmdb_page_top_lang
from cinephile.utils import datetimes
from cinephile.utils.movies import MovieCluster


class TmdbUrl(CrawlerUrl):
    @property
    def key_top250(self):
        return self._key_top250

    @property
    def key_detail(self):
        return self._key_detail

    def url(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        url = config["url"]
        if key == self._key_top250:
            page = kwargs.get("page")
            lang = kwargs.get("lang")
            if page:
                params = config["params_lang"] if lang else config["params"]
                params = params.format(page)
                return f"{url}?{params}"
            return url
        elif key == self._key_detail:
            return url.format(kwargs["mtype"], kwargs["movie_id"])
        return ""

    def source(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        url = config["url"]
        if key == self._key_detail:
            return url.format(kwargs["mtype"], kwargs["movie_id"])
        return url

    def _init_urls(self) -> dict:
        url_dict = {
            self._key_top250: {
                "desc": self.description,
                "url": "https://www.themoviedb.org/movie/top-rated",
                "params": "page={}",
                "params_lang": "page={}&language=zh-CN",
                "total": 250,
                "page_step": 20,
            },
            self._key_detail: {
                "desc": "TMDB电影详情页",
                "url": "https://www.themoviedb.org/{}/{}",
                "total": 1,
            },
        }
        return url_dict


class TmdbCrawler(BaseCrawler):
    def __init__(self, savedir=None, overwrite=False, **kwargs):
        super().__init__(savedir, overwrite, **kwargs)
        self.sitename = "tmdb"
        self.baseurl = "https://www.themoviedb.org"
        self.description = "TMDB高分电影 Top Rated Movies"
        self.urls = TmdbUrl(self.sitename, self.description)

    def parse_page(self, key, page, char_detect=False, **kwargs):
        if key == self.urls.key_top250:
            if kwargs["lang"]:
                return parse_tmdb_page_top_lang(page, **kwargs)
            else:
                return parse_tmdb_page_top(page, **kwargs)
        elif key == self.urls.key_detail:
            return parse_tmdb_page_detail(page, **kwargs)
        return None

    def process(self, key=None, savedir=None, **kwargs):
        if key == self.urls.key_top250:
            self.process_top250(savedir)
        elif key == self.urls.key_detail:
            self.process_detail(kwargs["movie_id"], savedir, mtype=kwargs.get("mtype", "movie"))

    def process_top250(self, savedir=None):
        key = self.urls.key_top250
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        total = url_config["total"]
        savename = self.getname(dt, name=f"{self.save_prefix_top}{total}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, savefile

        headers = self.get_headers()
        base_url = self.baseurl
        page_step = url_config["page_step"]
        page_cnt = int(math.ceil(total / page_step))
        movies = []
        titles = []
        for page_num in range(page_cnt):
            start = page_step * page_num
            page_num += 1
            if page_num % 3 == 0:
                headers = self.get_headers()
            for lang in [True, False]:
                url = self.get_url(key, lang=lang, page=page_num)
                page = self.get_page(url, headers, round_i=page_num, round_n=page_cnt, sleep_range=(3, 10))
                if not page:
                    logging.warning("page error")
                    continue
                if lang:
                    titles, next_url = self.parse_page(key, page, lang=lang)
                    if not titles or len(titles) != page_step:
                        logging.warning("Error titles")
                    logging.info(f"round={page_num}/{page_cnt}")
                else:
                    out, next_url = self.parse_page(key, page, lang=lang, base_url=base_url, titles=titles, start=start)
                    titles = []
                    if out:
                        movies.extend(out)

        movies = movies[:total]
        logging.info(f"save to data, top movies = {len(movies)}")
        desc = url_config["desc"]
        release = dt
        source = self.get_url(key, is_source=True)
        movie_cluster = MovieCluster(release, dt, desc, source, movies=movies)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_detail(self, movie_id, savedir=None, mtype="movie"):
        key = self.urls.key_detail
        dt = datetimes.utcnow()
        movie_id = str(movie_id)
        if "themoviedb.org/" in movie_id:
            mtype, movie_id = movie_id.split("themoviedb.org/")[-1].rstrip("/").split("/")
        movie_id2 = movie_id.split("-")[0]
        logging.info("TMDb Movie/TV = {} ({})".format(movie_id, mtype))

        savename = self.getname(dt, name=f"{self.save_prefix_movie}{mtype}{movie_id2}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        url_config = self.urls.query(key)
        headers = self.get_headers()
        url = self.get_url(key, movie_id=movie_id, mtype=mtype)
        page = self.get_page(url, headers)
        if not page:
            logging.warning("page error, exit\n\n")
            return self.error_http, None

        movie = self.parse_page(key, page, base_url=self.baseurl)
        if not movie:
            logging.warning("parser error, exit\n\n")
            return self.error_parse, None

        logging.info(f"save to data, movie detail = {movie.title}")
        desc = "{}({})".format(url_config["desc"], movie.title)
        source = self.get_url(key, movie_id=movie_id, mtype=mtype, is_source=True)
        movie_cluster = MovieCluster(dt, dt, desc, source, movie=movie)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile
