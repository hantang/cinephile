import logging
import math
import time
from pathlib import Path

from cinephile.crawlers.base import BaseCrawler, CrawlerUrl
from cinephile.crawlers.imdb_parser import extract_imdb_page_info
from cinephile.crawlers.imdb_parser import parse_imdb_page_list, parse_imdb_page_detail
from cinephile.crawlers.imdb_parser import parse_imdb_page_top_v4
from cinephile.utils import datetimes
from cinephile.utils.movies import MovieCluster


class ImdbUrl(CrawlerUrl):
    def __init__(self, sitename, description=None, baseurl=None):
        self.baseurl = baseurl
        super().__init__(sitename, description)

    @property
    def key_top250(self):
        return self._key_top250

    @property
    def key_list(self):
        return self._key_list

    @property
    def key_detail(self):
        return self._key_detail

    @property
    def key_hist(self):
        return self._key_hist

    def source(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        url = config["url"]
        if key == self._key_top250:
            return url
        elif key == self._key_detail:
            movie_id = kwargs["movie_id"]
            return url.format(movie_id)
        elif key == self._key_list:
            movie_list_id = kwargs["movie_list_id"]
            return url.format(movie_list_id)
        return ""

    def url(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        url = config["url"]
        if key == self._key_top250:
            return url
        elif key == self._key_detail:
            movie_id = kwargs["movie_id"]
            return url.format(movie_id)
        elif key == self._key_list:
            movie_list_id = kwargs.get("movie_list_id")
            params = kwargs.get("params")
            page = kwargs.get("page")
            if params:
                if params.startswith("http"):
                    return params
                else:
                    base_url = self.baseurl.rstrip("/")
                    params = params.lstrip("/")
                    return f"{base_url}/{params}"
            else:
                if not movie_list_id:
                    logging.warning(f"Error movie_list_id = {movie_list_id}")
                    exit(-1)

                url = url.format(movie_list_id)
                if page and page > 1:
                    params = config["params"].format(page)
                    return f"{url}?{params}"
                return url
        return ""

    def _init_urls(self) -> dict:
        url_dict = {
            self._key_top250: {
                "desc": "IMDb 电影Top250",
                "url": "https://www.imdb.com/chart/top/",
                "page_count": 1,
                "total": 250,
            },
            self.key_list: {
                # https://www.imdb.com/list/ls566275529/?page=3
                "desc": "IMDb 电影片单",
                "url": "https://www.imdb.com/list/{}/",
                "params": "page={}",
                "page_step": 100,
            },
            self._key_detail: {
                "desc": "IMDb 电影详情页",
                "url": "https://www.imdb.com/title/{}",
            },
            self._key_hist: {
                "url": "https://250.took.nl/history/",
            },
        }
        return url_dict


class ImdbCrawler(BaseCrawler):
    def __init__(self, savedir=None, overwrite=False, **kwargs):
        super().__init__(savedir, overwrite, **kwargs)
        self.sitename = "imdb"
        self.baseurl = "https://www.imdb.com/"
        self.description = "IMDb电影"
        self.urls = ImdbUrl(self.sitename, self.description, self.baseurl)

    def get_headers(self, agent="random"):
        headers = super().get_headers(agent)
        headers["Accept-Language"] = "en-US,en"
        return headers

    def parse_page(self, key, page, char_detect=False, **kwargs):
        page = super().parse_page(key, page, char_detect)
        if key == self.urls.key_top250:
            return parse_imdb_page_top_v4(page, **kwargs)
        elif key == self.urls.key_list:
            return parse_imdb_page_list(page, **kwargs)
        elif key == self.urls.key_detail:
            return parse_imdb_page_detail(page, **kwargs)
        # elif key == self.urls.key_hist:
        #     pass
        return None

    def process(self, key=None, savedir=None, **kwargs):
        if key == self.urls.key_top250:
            self.process_top250(savedir)
        elif key == self.urls.key_list:
            self.process_list(kwargs["movie_list_id"], savedir, page_limit=kwargs.get("page_limit", -1))
        elif key == self.urls.key_detail:
            self.process_detail(kwargs["movie_id"], savedir)

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
        url = self.get_url(key)
        page = self.get_page(url, headers)
        if not page:
            logging.warning("page error, exit\n\n")
            return self.error_http, savefile

        movies = self.parse_page(key, page, total=total, base_url=self.baseurl)
        if not movies:
            logging.warning("parser error, exit\n\n")
            return self.error_parse, savefile

        logging.info(f"save to data, top movies = {len(movies)}")
        desc = url_config["desc"]
        source = self.get_url(key, is_source=True)
        movie_cluster = MovieCluster(dt, dt, desc, source, movies=movies)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_detail(self, movie_id, savedir=None):
        # todo parse page
        key = self.urls.key_detail
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        savename = self.getname(dt, name=f"{self.save_prefix_movie}{movie_id}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        url = self.get_url(key, movie_id=movie_id)
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
        source = self.get_url(key, movie_id=movie_id, is_source=True)
        movie_cluster = MovieCluster(dt, dt, desc, source, movie=movie)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_list(self, movie_list_id, savedir=None, page_limit=-1):
        """
        self.baseurl = "https://www.imdb.com/list/ls027841309/"
        self.params = "sort=list_order,asc&st_dt=&mode=detail&page={}"
        """
        key = self.urls.key_list
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        savename = self.getname(dt, name=f"{self.save_prefix_list}{movie_list_id}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        page_step = url_config["page_step"]

        page_num = 1
        page_cnt = -1
        list_desc = None
        movies = []
        next_url = self.get_url(key, movie_list_id=movie_list_id, page=page_num)
        while page_limit <= 0 or page_num <= page_limit:
            if page_num % 10 == 1:
                headers = self.get_headers()
                headers['Host'] = 'www.imdb.com'
                headers['Accept-Language'] = 'en-US,en;q=0.5'
                if page_limit > 1:
                    time.sleep(3)

            url = next_url
            page = self.get_page(url, headers, round_i=page_num, round_n=page_cnt)
            if not page:
                if page_num > 1:
                    break
                logging.warning("page error, exit\n\n")
                return self.error_http, None

            if page_num == 1:
                total_num, list_desc = extract_imdb_page_info(page)
                page_cnt = int(math.ceil(total_num / page_step))
                logging.info(f"total items = {total_num} page = {page_cnt}")

            logging.info(f"round={page_num}/{page_cnt} parse page, page={len(page)}")
            out, next_url = self.parse_page(key, page, total=page_step, base_url=self.baseurl)
            if out:
                movies.extend(out)
            if not (out and next_url) or next_url == "#":
                break
            page_num += 1
            next_url = self.get_url(key, params=next_url, page=page_num)

        logging.info(f"save to data, top movies = {len(movies)}")
        desc = "\n".join([list_desc[k] for k in ["name", "author"]]) if list_desc else url_config["desc"]
        source = self.get_url(key, movie_list_id=movie_list_id, is_source=True)
        movie_cluster = MovieCluster(dt, dt, desc, source, movies=movies)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile
