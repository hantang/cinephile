import logging
from pathlib import Path
from typing import List, Union

from cinephile.crawlers.base import BaseCrawler, CrawlerUrl
from cinephile.crawlers.douban_parser import extract_page_info
from cinephile.crawlers.douban_parser import parse_page_top250, parse_page_list
from cinephile.crawlers.douban_parser import parse_page_detail, parse_page_hot
from cinephile.utils import datetimes
from cinephile.utils.movies import MovieCluster


class DoubanUrl(CrawlerUrl):
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
    def key_hot(self):
        return self._key_hot

    def url(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]

        if key in [self._key_top250, self._key_list]:
            url = config["url"]
            if key == self._key_list:
                movie_list_id = kwargs["movie_list_id"]
                url = url.format(movie_list_id)

            if "params" in kwargs:
                params = kwargs["params"]
                params = params.lstrip("?")
                return f"{url}?{params}"

            start = kwargs.get("start")
            if start is None or start == 0:
                return url
            else:
                params = config["params"].format(start)
                return f"{url}?{params}"
        elif key == self._key_detail:
            url = config["url"]
            movie_id = kwargs["movie_id"]
            return url.format(movie_id)
        elif key == self._key_hot:
            order = kwargs.get("order", 0)
            url = config["url"]
            params = config["params"]
            url_id = config["collections"][order]["id"]
            url = url.format(url_id)
            return f"{url}?{params}"
        return ""

    def source(self, key: str, **kwargs) -> Union[str, List[str]]:
        config = self.url_dict[key]
        if key in [self._key_top250, self._key_list, self._key_detail]:
            url = config["url"]
            if key == self._key_list:
                movie_list_id = kwargs["movie_list_id"]
                url = url.format(movie_list_id)
            if key == self._key_detail:
                movie_id = kwargs["movie_id"]
                url = url.format(movie_id)
            return url
        elif key == self._key_hot:
            order = kwargs.get("order", 0)
            raw_url = config["raw_url"]
            if order == -1:
                return raw_url[0]
            url_id = config["collections"][order]["id"]
            url = [raw_url[0], raw_url[1].format(url_id)]
            return url
        return ""

    def _init_urls(self) -> dict:
        url_dict = {
            self._key_top250: {
                "desc": "豆瓣电影Top250",
                "url": "https://movie.douban.com/top250/",
                "params": "start={}&filter=",
                "page_start": 1,
                "page_end": 10,
                "page_step": 25,
                "total": 250,
            },
            self._key_list: {
                "desc": "豆瓣豆列（片单）",
                "url": "https://www.douban.com/doulist/{}/",
                "params": "start={}&sort=time&playable=0&sub_type=",
                "page_step": 25,
            },
            self._key_detail: {
                "desc": "豆瓣电影详情页",
                "url": "https://movie.douban.com/subject/{}/",
                "params": "",
                "total": 1,
            },
            self._key_hot: {
                "desc": "豆瓣电影实时和近期热门榜单（手机版）",
                "url": "https://m.douban.com/rexxar/api/v2/subject_collection/{}/items",
                "params": "start=0&count=50&updated_at=&items_only=1&for_mobile=1",
                "base_url": "https://m.douban.com/",
                "raw_url": [
                    "https://movie.douban.com/chart",
                    "https://m.douban.com/subject_collection/{}",
                ],
                "total": 20,
                "count": 6,
                "collections": [
                    {"desc": "实时热门电影（20部）", "id": "movie_real_time_hotest"},
                    {"desc": "实时热门书影音（20个）", "id": "subject_real_time_hotest"},
                    {"desc": "一周口碑电影榜（10部）", "id": "movie_weekly_best"},
                    {"desc": "近期热门电影榜（20部）", "id": "ECPE465QY"},
                    {"desc": "近期高分电影榜（20部）", "id": "EC7Q5H2QI"},
                    {"desc": "近期冷门佳片榜（20部）", "id": "ECSU5CIVQ"},
                ],
            },
        }
        return url_dict


class DoubanCrawler(BaseCrawler):
    """
    1. 豆瓣电影Top250: "https://movie.douban.com/top250?start={}&filter=",
    2. 豆列（片单）
    3. 电影详情页
    4. 豆瓣热门
    """

    def __init__(self, savedir=None, overwrite=False, **kwargs):
        super().__init__(savedir, overwrite, **kwargs)
        self.sitename = "douban"
        self.baseurl = "https://movie.douban.com/"
        self.description = "豆瓣电影"
        self.urls = DoubanUrl(self.sitename, self.description)

    def parse_page(self, key, page, char_detect=False, **kwargs):
        page = super().parse_page(key, page, char_detect)
        if key == self.urls.key_top250:
            return parse_page_top250(page, **kwargs)
        elif key == self.urls.key_hot:
            return parse_page_hot(page, **kwargs)
        elif key == self.urls.key_list:
            return parse_page_list(page, **kwargs)
        elif key == self.urls.key_detail:
            return parse_page_detail(page, **kwargs)
        return None

    def process(self, key=None, savedir=None, **kwargs):
        if key == self.urls.key_top250:
            self.process_top250(savedir)
        elif key == self.urls.key_list:
            self.process_list(kwargs["movie_list_id"], savedir, page_limit=kwargs.get("page_limit", -1))
        elif key == self.urls.key_detail:
            self.process_detail(kwargs["movie_id"], savedir)
        elif key == self.urls.key_hot:
            self.process_hot(savedir)

    def process_top250(self, savedir=None):
        key = self.urls.key_top250
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        total = url_config["total"]
        savename = self.getname(dt, name=f"{self.save_prefix_top}{total}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        page_start = url_config["page_start"]
        page_end = url_config["page_end"]
        page_step = url_config["page_step"]
        log = "process {}".format(url_config["desc"])
        logging.info(f"{log}, page= {page_start} ~ {page_end}")

        url = self.get_url(key, start=None)
        page = self.get_page(url, headers, round_i=page_start, round_n=page_end)
        if not page:
            logging.warning("page error, exit\n\n")
            return self.error_http, None

        more_hrefs, dou_desc = extract_page_info(page, desc="Top250")
        movies = self.parse_page(key, page, total=page_step)
        if not (movies and more_hrefs):
            return self.error_parse, None
        rn = len(more_hrefs)
        log = "more_hrefs (total={}): {} ...".format(rn, more_hrefs[:2])
        logging.info(log)

        for num, href in enumerate(more_hrefs):
            url = href if href.startswith("http") else self.urls.url(key, params=href)
            ri = 1 + num + page_start
            page = self.get_page(url, headers, round_i=ri, round_n=page_end)
            if not page:
                continue
            logging.info(f"round={1 + num}/{rn} parse page, page={len(page)}")
            out = self.parse_page(key, page, total=page_step)
            if out:
                movies.extend(out)

        logging.info(f"save to data, top movies = {len(movies)}")
        desc = dou_desc["name"]
        source = self.get_url(key, is_source=True)
        movie_cluster = MovieCluster(dt, dt, desc, source, movies=movies)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_list(self, movie_list_id, savedir=None, page_limit=-1):
        key = self.urls.key_list
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        savename = self.getname(dt, name=f"{self.save_prefix_list}{movie_list_id}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        page_step = url_config["page_step"]
        url = self.get_url(key, movie_list_id=movie_list_id, start=None)
        page = self.get_page(url, headers, round_i=1, round_n=1)
        if not page:
            logging.warning("page error, exit\n\n")
            return self.error_http, None

        more_hrefs, dou_desc = extract_page_info(page, desc="douban movie list")
        movies = self.parse_page(key, page, total=page_step)
        if not movies:
            return self.error_parse, None
        logging.info(f"total more_hrefs = {len(more_hrefs)} / {page_limit}")
        if page_limit >= 0:
            more_hrefs = more_hrefs[:page_limit]
        rn = len(more_hrefs)
        log = "more_hrefs (total={}): {} ...".format(rn, more_hrefs[:2])
        logging.info(log)

        for num, href in enumerate(more_hrefs):
            url = href if href.startswith("http") else self.urls.url(key, params=href)
            page = self.get_page(url, headers, round_i=1 + num, round_n=rn)
            if not page:
                continue
            logging.info(f"round={1 + num}/{rn}parse page, page={len(page)}")
            out = self.parse_page(key, page, total=page_step)
            if out:
                movies.extend(out)

        logging.info(f"save to data, movie list = {len(movies)}")
        desc = "\n".join([dou_desc[v] for v in ["name", "author", "about"]]).strip()
        source = self.get_url(key, is_source=True, movie_list_id=movie_list_id)
        release_time = dou_desc["author"].split()[3]
        movie_cluster = MovieCluster(release_time, dt, desc, source, movies=movies)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_detail(self, movie_id, savedir=None):
        key = self.urls.key_detail
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        savename = self.getname(dt, name=f"{self.save_prefix_movie}{movie_id}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        url = self.get_url(key, movie_id=movie_id)
        page = self.get_page(url, headers, round_i=1, round_n=1)
        if not page:
            logging.warning("page error, exit\n\n")
            return self.error_http, None
        logging.info(f"parse page, page={len(page)}")

        movie = self.parse_page(key, page)
        if not movie:
            return self.error_parse, None
        desc = "{}({})".format(url_config["desc"], movie.title)
        source = self.get_url(key, is_source=True, movie_id=movie_id)
        movie_cluster = MovieCluster(dt, dt, desc, source, movie=movie)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_hot(self, savedir=None):
        key = self.urls.key_hot
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        savename = self.getname(dt, name="weekly-hot")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        headers["Referer"] = url_config["base_url"]
        count = url_config["count"]
        clusters = []
        for i in range(count):
            url = self.get_url(key, order=i)
            page = self.get_page(
                url, headers=headers, page_format="json", round_i=i + 1, round_n=count
            )
            if not page:
                logging.warning("{} page error \n{}\n".format(url_config["desc"], "-" * 50))
                continue
            desc = url_config["collections"][i]["desc"]  # todo get_desc
            items, entries = self.parse_page(key, page, desc=desc)
            source = self.get_url(key, is_source=True, order=i)

            movie_cluster = MovieCluster(
                dt, dt, desc, source, movies=entries, draft=items
            )
            clusters.append(movie_cluster)

        logging.info(f"save to data, cluster = {len(clusters)}")
        if not clusters:
            return self.error_parse, None

        desc = url_config["desc"]
        source = self.get_url(key, is_source=True, order=-1)
        movie_cluster = MovieCluster(dt, dt, desc, source, cluster=clusters)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile
