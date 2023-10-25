import logging
import math
from pathlib import Path

from bs4 import BeautifulSoup

from cinephile.crawlers.base import BaseCrawler, CrawlerUrl
from cinephile.utils import datetimes
from cinephile.utils.movies import MovieCluster, Movie
from cinephile.utils.texts import strip


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
                params = config["params-lang"] if lang else config["params"]
                params = params.format(page)
                return f"{url}?{params}"
            return url
        elif key == self._key_detail:
            movie_id = kwargs["movie_id"]
            return url.format(movie_id)
        return ""

    def source(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        url = config["url"]
        if key == self._key_detail:
            return url.format(kwargs["movie_id"])
        return url

    def _init_urls(self) -> dict:
        url_dict = {
            self._key_top250: {
                "desc": self.description,
                "url": "https://www.themoviedb.org/movie/top-rated",
                "params": "page={}",
                "params-lang": "page={}&language=zh-CN",
                "total": 250,
                "page_step": 20,
            },
            self._key_detail: {  # todo
                "desc": "TMDB电影详情页",
                # https://www.themoviedb.org/movie/207-dead-poets-society
                "url": "https://www.themoviedb.org/movie/{}",
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
        return None

    def process(self, key=None, savedir=None, **kwargs):
        if key == self.urls.key_top250:
            self.process_top250(savedir)
        if key == self.urls.key_detail:
            self.process_detail(kwargs["movie_id"], savedir)

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
        base_url = self.baseurl
        page_step = url_config["page_step"]
        page_cnt = int(math.ceil(total / page_step))
        movies = []
        titles = []
        for page_num in range(page_cnt):
            start = page_step * page_num
            page_num += 1
            for lang in [True, False]:
                url = self.get_url(key, lang=lang, page=page_num)
                page = self.get_page(url, headers, round_i=page_num, round_n=page_cnt)
                if not page:
                    logging.warning("page error")
                    continue
                if lang:
                    titles, next_url = self.parse_page(key, page, lang=lang)
                    if not titles or len(titles) != page_step:
                        logging.warning("Error titles")
                    logging.info(f"round={page_num}/{page_cnt} Titles = {titles}")
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

    def process_detail(self, movie_id, savedir=None):
        key = self.urls.key_detail


def parse_tmdb_page_top_lang(page, **kwargs):
    soup = BeautifulSoup(page, "html.parser")
    logging.info("Title = {}".format(soup.title.text.strip()))

    div_content = soup.body.find("div", class_="content_wrapper")
    div_page = div_content.find("div", class_="page_wrapper")
    if not div_page:
        return None
    next_url = div_page.find("p", class_="load_more").a["href"]
    items_raw = div_page.find_all("div", class_="card")
    items = [item for item in items_raw if " ".join(item["class"]) == "card style_1"]
    logging.info(f"items = {len(items)}/{len(items_raw)}")
    titles = [strip(item.find("div", class_="content").h2.text) for item in items]
    logging.info(f"next url = {next_url}")
    return titles, next_url


def parse_tmdb_page_top(page, **kwargs):
    start = kwargs["start"]
    base_url = kwargs["base_url"]
    titles = kwargs["titles"]

    soup = BeautifulSoup(page, "html.parser")
    div_content = soup.body.find("div", class_="content_wrapper")
    div_page = div_content.find("div", class_="page_wrapper")
    if not div_page:
        return None
    items_raw = div_page.find_all("div", class_="card")
    items = [item for item in items_raw if " ".join(item["class"]) == "card style_1"]
    logging.info(f"items = {len(items)}/{len(items_raw)}")
    next_url = div_page.find("p", class_="load_more").a["href"]

    entries = []
    for i, item in enumerate(items):
        rank = start + i + 1
        div_image = item.find("div", class_="image")
        tmdb_id = div_image.a["href"].strip().split("?")[0]
        link = base_url + tmdb_id
        img = base_url + div_image.img["src"].strip()
        tmdb_id = tmdb_id.strip("/").split("/")[-1]

        div_content = item.find("div", class_="content")
        title = strip(div_content.h2.text)
        date = strip(div_content.p.text)
        year = date.split(",")[-1].strip()[:4]
        if year.isdigit():
            year = int(year)
        else:
            logging.warning(f"Error year {title}, {year}")
            year = 0
        score = div_content.find("div", class_="user_score_chart")["data-percent"]
        score = {
            "tmdb-score": score,
        }
        more = {
            "tmdb_id": tmdb_id,
            "date": date,
        }
        if titles:
            more["title-more"] = titles[i]
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

    return entries, next_url
