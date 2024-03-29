import logging
import math
import time
from pathlib import Path
from typing import List, Union

from cinephile.crawlers.base import BaseCrawler, CrawlerUrl
from cinephile.parsers.douban_parser import extract_page_info
from cinephile.parsers.douban_parser import parse_page_detail, parse_page_hot
from cinephile.parsers.douban_parser import parse_page_top250, parse_page_list
from cinephile.parsers.douban_parser2 import parse_annual_data
from cinephile.utils import datetimes
from cinephile.utils.movies import MovieCluster


class DoubanUrl(CrawlerUrl):
    def __init__(self, sitename, description=None):
        self._key_annual = f"{sitename}-annual"
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
    def key_hot(self):
        return self._key_hot

    @property
    def key_annual(self):
        return self._key_annual

    def url(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]

        if key in [self._key_top250, self._key_list]:
            url = config["url"]
            params = kwargs.get("params")
            start = kwargs.get("start")

            if params and params.startswith("http"):
                return params

            if key == self._key_list:
                movie_list_id = kwargs["movie_list_id"]
                url = url.format(movie_list_id)

            if params:
                params = params.lstrip("?")
                return f"{url}?{params}"

            if start is None or start in [0, 1]:
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
        elif key == self._key_annual:
            year = kwargs["year"]
            urls = config["urls"]
            if year == 2014:
                return urls[0]
            elif year <= 2022:
                return urls[1].format(year)
            else:
                return urls[2]
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
                if movie_id.startswith("http"):
                    return movie_id
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
        elif key == self._key_annual:
            year = kwargs["year"]
            urls = config["raw_urls"]
            if year == 2014:
                return urls[0]
            elif year <= 2016:
                return urls[1].format(year)
            else:
                return urls[2].format(year)
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
                "desc": "豆瓣电影实时和近期热门榜单",
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
            self._key_annual: {
                "desc": "豆瓣电影年度榜单",
                "urls": [
                    "https://movie.douban.com/review2014",  # 2014 html
                    "https://movie.douban.com/ithil_j/activity/movie_annual{}?with_widgets=1",  # 2015~2022 json
                    "https://movie.douban.com/j/neu/page/22/"  # 2023 json
                ],
                "raw_urls": [
                    "https://movie.douban.com/review2014",  # 2014
                    "https://movie.douban.com/annual{}",  # 2015~2016
                    "https://movie.douban.com/annual/{}",  # 2017~
                ]
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

    def get_headers(self, agent="random", **kwargs):
        headers = super().get_headers(agent)
        if kwargs.get("key") == self.urls.key_hot:
            headers["Referer"] = kwargs["referer"]
        return headers

    def parse_page(self, key, page, char_detect=False, **kwargs):
        if char_detect:
            page = super().parse_page(key, page, char_detect)

        if key == self.urls.key_top250:
            return parse_page_top250(page, **kwargs)
        elif key == self.urls.key_hot:
            return parse_page_hot(page, **kwargs)
        elif key == self.urls.key_list:
            return parse_page_list(page, **kwargs)
        elif key == self.urls.key_detail:
            return parse_page_detail(page, **kwargs)
        elif key == self.urls.key_annual:
            return parse_annual_data(page, **kwargs)
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

    def process_top(self, savedir=None):
        return self.process_top250(savedir)

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
        page_num = url_config["page_start"]
        page_cnt = url_config["page_end"]
        page_step = url_config["page_step"]
        dou_desc = None
        movies = []
        next_url = self.get_url(key, start=page_num)
        while True:
            url = next_url
            page = self.get_page(url, headers, round_i=page_num, round_n=page_cnt)
            if not page:
                if page_num > 1:
                    break
                logging.warning("page error, exit\n\n")
                return self.error_http, savefile

            if page_num == 1:
                more_hrefs, dou_desc = extract_page_info(page)
                total_num = dou_desc.get("count", total)
                page_cnt = int(math.ceil(total_num / page_step))
                logging.info(f"total items = {total_num} page = {page_cnt}")

            logging.info(f"round={page_num}/{page_cnt} parse page, page bytes={len(page)}")
            out, next_url = self.parse_page(key, page, total=page_step)
            logging.info("out = {}, next_url = {}".format(len(out) if out else None, next_url))
            if out:
                movies.extend(out)
            if not (out and next_url) or next_url == "#":
                break
            page_num += 1
            next_url = self.get_url(key, params=next_url, start=page_num)

        logging.info(f"save to data, top movies = {len(movies)}")
        desc = dou_desc["name"]
        source = self.get_url(key, is_source=True)
        movie_cluster = MovieCluster(dt, dt, desc, source, movies=movies)
        if movie_cluster.total != total:
            logging.error("Douban top 250 data is error")
            return self.error_count, None

        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_list(self, movie_list_id, savedir=None, page_limit=-1):
        key = self.urls.key_list
        dt = datetimes.utcnow()
        movie_list_id = str(movie_list_id)
        if "doulist" in movie_list_id:
            movie_list_id = movie_list_id.strip("/").split("doulist/")[-1]
        if not movie_list_id.isdigit():
            logging.warning(f"Error doulist id = {movie_list_id}")
            exit(-1)

        url_config = self.urls.query(key)
        savename = self.getname(dt, name=f"{self.save_prefix_list}{movie_list_id}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, None

        headers = self.get_headers()
        page_step = url_config["page_step"]

        page_num = 1
        page_cnt = -1
        dou_desc = None
        movies = []
        next_url = self.get_url(key, movie_list_id=movie_list_id, start=page_num)
        while page_limit <= 0 or page_num <= page_limit:
            url = next_url
            if page_num % 10 == 0:
                headers = self.get_headers()
            page = self.get_page(url, headers, round_i=page_num, round_n=page_cnt, sleep_range=(1, 5))
            if not page:
                if page_num > 1:
                    break
                logging.warning("page error, exit\n\n")
                return self.error_http, None

            if page_num == 1:
                more_hrefs, dou_desc = extract_page_info(page)
                total_num = dou_desc.get("count", 200)
                page_cnt = int(math.ceil(total_num / page_step))
                logging.info(f"total items = {total_num} page = {page_cnt}")

            logging.info(f"round={page_num}/{page_cnt} parse page, page bytes={len(page)}")
            out, next_url = self.parse_page(key, page, total=page_step)
            logging.info("out = {}, next_url = {}".format(len(out) if out else None, next_url))
            if out:
                movies.extend(out)
            if not (out and next_url) or next_url == "#":
                break
            page_num += 1
            next_url = self.get_url(key, params=next_url, start=page_num)

        logging.info(f"save to data, movie list = {len(movies)}")
        desc = "\n".join([dou_desc[v] for v in ["name", "author", "about"]]).strip() if dou_desc else url_config["desc"]
        source = self.get_url(key, is_source=True, movie_list_id=movie_list_id)
        release_time = dou_desc["author"].split()[3]
        movie_cluster = MovieCluster(release_time, dt, desc, source, movies=movies)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_detail(self, movie_id, savedir=None):
        key = self.urls.key_detail
        dt = datetimes.utcnow()
        movie_id = str(movie_id)
        if "subject" in movie_id:
            movie_id = movie_id.strip("/").split("subject/")[-1]
        if not movie_id.isdigit():
            logging.warning(f"Error douban movie id = {movie_id}")
            return self.error_param, None

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

    def process_detail_list(self, movie_id_list, savedir=None, postfix=None):
        key = self.urls.key_detail
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        postfix = ("-" + postfix) if postfix else ""
        movie_cnt = len(movie_id_list)
        savename = self.getname(dt, name=f"{self.save_prefix_movie}-cnt{movie_cnt}{postfix}")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, savefile
        headers = None
        movies = []
        for i, movie_id in enumerate(movie_id_list):
            if i % 10 == 0:
                headers = self.get_headers()
                if i > 0:
                    time.sleep(2)
            url = self.get_url(key, movie_id=movie_id)
            page = self.get_page(url, headers, round_i=1, round_n=1, sleep_range=(2, 6))
            if not page:
                logging.warning("page error, exit\n\n")
                # return self.error_http, None
                continue
            logging.info(f"parse page, page={len(page)}")

            movie = self.parse_page(key, page)
            if not movie:
                continue
            movies.append(movie)

        desc = url_config["desc"]
        source = self.baseurl
        movie_cluster = MovieCluster(dt, dt, desc, source, movies=movies)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_hot(self, savedir=None):
        key = self.urls.key_hot
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        savename = self.getname(dt, name="weekly-hot")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, savefile

        headers = self.get_headers(key=key, referer=url_config["base_url"])
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
            return self.error_parse, savefile

        desc = url_config["desc"]
        source = self.get_url(key, is_source=True, order=-1)
        movie_cluster = MovieCluster(dt, dt, desc, source, cluster=clusters)
        self.save(savefile, movie_cluster)
        return movie_cluster.total, savefile

    def process_annual(self, year, savedir=None, save_csv=True):
        assert year >= 2014
        key = self.urls.key_annual
        dt = datetimes.utcnow()
        url_config = self.urls.query(key)
        logging.info(f"process douban annual movies, year = {year}")

        savename = self.getname(dt, name=f"annual{year}", datetime=False)
        savename_csv = self.getname(dt, name=f"annual{year}", suffix="csv", datetime=False)
        savefile = Path(savedir if savedir else self.savedir, savename)
        # savefile_csv = Path(savedir if savedir else self.savedir, savename_csv)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, savefile

        headers = self.get_headers()
        url = self.get_url(key, year=year)
        logging.info(f"url = {url}")

        page = self.get_page(url, headers=headers, page_format="json" if year >= 2015 else "text")
        if not page:
            logging.warning("page error, exit\n\n")
            return self.error_http, savefile

        items_list, entries_list, groups = self.parse_page(key, page, year=year)

        n = len(items_list)
        if n == 0:  # or df is None:
            logging.warning("Error dataframe is null")
            return self.error_parse, savefile

        clusters = []
        for i in range(n):
            items, entries, desc = items_list[i], entries_list[i], groups[i]
            movie_cluster = MovieCluster(dt, dt, desc, None, movies=entries, draft=items)
            clusters.append(movie_cluster)
        desc = url_config["desc"] + f": 豆瓣{year}年度"
        source = self.get_url(key, is_source=True, order=-1, year=year)
        movie_cluster = MovieCluster(dt, dt, desc, source, cluster=clusters)
        self.save(savefile, movie_cluster)
        # if save_csv:
        #     self.save(savefile_csv, movie_cluster=None, dataframe=df)
        return movie_cluster.total, savefile
