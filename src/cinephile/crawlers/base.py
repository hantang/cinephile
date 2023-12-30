import json
import logging
from abc import abstractmethod
from pathlib import Path
from typing import Union, Optional

from bs4.dammit import UnicodeDammit

from cinephile.utils import datetimes
from cinephile.utils.download import download_page, download_sleep, get_ua
from cinephile.utils.movies import MovieCluster


class CrawlerUrl:
    def __init__(self, sitename, description=None):
        self.sitename = sitename
        self._key_top250 = f"{self.sitename}-top250"
        self._key_top100 = f"{self.sitename}-top100"
        self._key_detail = f"{self.sitename}-detail"
        self._key_list = f"{self.sitename}-list"
        self._key_hot = f"{self.sitename}-hot"
        self._key_hist = f"{self.sitename}-hist"
        self.description = description
        self.url_dict = self._init_urls()

    def query(self, key):
        return self.url_dict[key]

    @abstractmethod
    def url(self, key: str, **kwargs) -> str:
        pass

    @abstractmethod
    def source(self, key: str, **kwargs) -> str:
        pass

    @abstractmethod
    def _init_urls(self) -> dict:
        pass


# todo ABCMeta
class BaseCrawler:
    def __init__(
            self, savedir: Union[str, Path] = None, overwrite: bool = False, **kwargs
    ):
        self.sitename = ""
        self.baseurl = ""
        self.description = ""
        self.dt = datetimes.utcnow()
        self.overwrite = overwrite
        self.savedir = savedir if savedir else Path(".")
        self.urls = CrawlerUrl(self.sitename, self.description)

        self.save_prefix_base = "movie"
        self.save_prefix_top = "top"
        self.save_prefix_movie = "mid"
        self.save_prefix_list = "mlist"

        self.error_http = -1
        self.error_file_exist = -2
        self.error_parse = -3
        self.error_param = -4
        self.error_other = -10
        self.user_agent = "User-Agent"
        logging.info(f"now = {self.dt}")

    def get_headers(self, agent="random"):
        val = get_ua(agent)
        headers = {self.user_agent: val}
        return headers

    def get_url(self, key, is_source=False, **kwargs):
        if is_source:
            return self.urls.source(key, **kwargs)
        else:
            return self.urls.url(key, **kwargs)

    def get_page(
            self,
            url,
            headers,
            params=None,
            page_format="text",
            retry=1,
            sleep_opt="random",
            sleep_range=None,
            **kwargs,
    ):
        for i in range(retry):
            if "round_i" not in kwargs:
                kwargs["round_i"] = 1
            if "round_n" not in kwargs:
                kwargs["round_n"] = 1
            round_i = kwargs["round_i"]
            round_n = kwargs["round_n"]
            page, status = download_page(url, headers, params, page_format, **kwargs)
            if round_i < round_n or round_n == -1:
                download_sleep(round_i, sleep_opt, sleep_range)
            if page:
                return page
            elif i + 1 < retry:
                download_sleep(round_i, 30)  # retry after 30 seconds
        return None

    # @abstractmethod
    def parse_page(self, key, page, char_detect=False, **kwargs):
        if char_detect:
            return UnicodeDammit.detwingle(page)
        return page

    @abstractmethod
    def process(self, key=None, savedir=None, **kwargs):
        pass

    def getname(self, dt=None, name=None, post=None, suffix="json", datetime=True):
        # douban-movie-top250-v20230101.json, douban-movie-dl1234-v2023.json
        suffix = suffix.strip().strip(".").strip()
        dt2 = datetimes.time2str(dt if dt else self.dt, 3)
        category = name if name else ""
        post = "" if not post else post
        parts = [self.sitename, self.save_prefix_base, category, post]
        if datetime:
            parts.append("v" + dt2)
        parts = "-".join([v for v in parts if len(v) > 0])
        savename = f"{parts}.{suffix}"
        return savename

    def check(self, filename):
        if Path(filename).exists():
            logging.warning(f"save file exists, file={filename}")
            return True
        return False

    def save(self, savefile, movie_cluster: Optional[MovieCluster], **kwargs):
        # todo save
        filename = Path(savefile)
        if not filename.parent.exists():
            logging.info(f"create dir = {filename.parent}")
            filename.parent.mkdir(parents=True)
        logging.info(f"save to {filename}")

        if movie_cluster is None and 'dataframe' in kwargs:
            df = kwargs['dataframe']
            logging.info(f"save dataframe to csv, df={df.shape}")
            df.to_csv(filename, index=False)
        else:
            data = movie_cluster.to_dict()
            logging.info(f"data keys = {data.keys()}")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        logging.info("save done\n\n")
