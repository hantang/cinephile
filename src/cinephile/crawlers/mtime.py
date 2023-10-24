import logging
from pathlib import Path

from cinephile.crawlers.base import BaseCrawler, CrawlerUrl
from cinephile.crawlers.mtime_parser import parse_mtime_json_detail, parse_mtime_json_top
from cinephile.utils import datetimes
from cinephile.utils.misc import set_logging
from cinephile.utils.movies import MovieCluster


class MtimeUrl(CrawlerUrl):
    @property
    def key_top100(self):
        return self._key_top100

    @property
    def key_detail(self):
        return self._key_detail

    def url(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        tt = datetimes.tsnow()
        url = config["url"]
        params = config["params"]
        if key == self._key_detail:
            movie_id = kwargs["movie_id"]
            params = params.format(tt, movie_id)
        else:
            params = params.format(tt)
        return f"{url}?{params}"

    def source(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        raw_url = config["raw_url"]
        if key == self._key_detail:
            movie_id = kwargs["movie_id"]
            return raw_url.format(movie_id)
        return raw_url

    def _init_urls(self) -> dict:
        url_dict = {
            self._key_top100: {
                "desc": self.description,
                "url": "http://front-gateway.mtime.com/library/index/app/topList.api",
                "params": "tt={}",
                "raw_url": "http://list.mtime.com/listIndex",
                "old_url": "http://www.mtime.com/top/movie/top100/",
                "page_count": 1,
                "total": 100,
                "top_limit": 4,
                "page_format": "json",
            },
            self._key_detail: {
                "desc": "时光电影详情页",
                "url": "http://front-gateway.mtime.com/library/movie/detail.api",
                "params": "tt={}&movieId={}&locationId=290",
                "raw_url": "http://movie.mtime.com/{}",
                "total": 1,
                "page_format": "json",
            },
        }
        return url_dict


class MtimeCrawler(BaseCrawler):
    def __init__(self, savedir=None, overwrite=False):
        super(MtimeCrawler, self).__init__(savedir, overwrite)
        self.sitename = "mtime"
        self.baseurl = "http://www.mtime.com/"
        self.description = "时光电影榜单Top100"
        self.urls = MtimeUrl(self.sitename, self.description)

    def parse_page(self, key, page, char_detect=False, **kwargs):
        # updateTime = datetime.datetime.fromtimestamp(int(page["data"]["created"]) // 1000)
        if key == self.urls.key_top100:
            return parse_mtime_json_top(page, **kwargs)
        elif key == self.urls.key_detail:
            return parse_mtime_json_detail(page)

    def process(self, key=None, savedir=None, **kwargs):
        if key == self.urls.key_top100:
            self.process_top100(savedir)
        elif key == self.urls.key_detail:
            self.process_detail(kwargs["movie_id"], savedir)

    def process_top100(self, savedir=None):
        key = self.urls.key_top100
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        total = url_config['total']
        savename = self.getname(dt, name=f"{self.save_prefix_top}{total}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        url = self.get_url(key)
        page = self.get_page(url, headers=headers, page_format="json")
        if not page:
            return self.error_parse, None

        logging.info(f"parse page, page={len(page)}")
        top_limit = url_config['top_limit']
        cluster = []
        tops = page["data"]["movieTopList"]["topListInfos"]
        for i in range(top_limit):
            logging.info(f"get top list = {i}")
            movies = self.parse_page(key, page, order=i)
            if not movies:
                continue

            draft = tops[i]
            desc = " ".join([draft["title"], draft["subTitle"]])
            release = draft["modifyTime"]
            source = self.get_url(key, is_source=True)
            movie_cluster = MovieCluster(release, dt, desc, source, movies=movies)
            cluster.append(movie_cluster)

        if not cluster:
            logging.warning("{} page error \n{}\n".format(url_config["desc"], "-" * 50))

        source = self.get_url(key, is_source=True)
        main_desc = tops[0]["description"]
        main_release = tops[0]["modifyTime"]
        movie_cluster = MovieCluster(main_release, dt, main_desc, source, cluster=cluster)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_detail(self, movie_id, savedir=None):
        key = self.urls.key_detail
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        savename = self.getname(dt, name=f"{self.save_prefix_movie}{movie_id}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        logging.info(f"savefile = {savefile}")
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        url = self.get_url(key, movie_id=movie_id)
        page = self.get_page(url, headers, page_format="json")
        if not page:
            logging.warning("page error, exit\n\n")
            return self.error_parse, None

        movie = self.parse_page(key, page)
        desc = "{}({})".format(url_config["desc"], movie.title)
        source = self.get_url(key, is_source=True, movie_id=movie_id)
        movie_cluster = MovieCluster(dt, dt, desc, source, movie=movie)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile
