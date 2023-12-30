import logging
import math
from pathlib import Path

from bs4 import BeautifulSoup

from cinephile.crawlers.base import BaseCrawler, CrawlerUrl
from cinephile.utils import datetimes
from cinephile.utils.movies import MovieCluster, Movie, MovieTag
from cinephile.utils.texts import strip, extract_year


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
                "params-lang": "page={}&language=zh-CN",
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
    tag = MovieTag.TMDB_TOP
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
        more = {
            "tmdb-url": link,
            "tmdb-cover": img,
            "tmdb-id": tmdb_id,
            "tmdb-score": score,
            "tmdb-date": date,
        }
        if titles:
            more["tmdb-titles"] = [titles[i]]
        category = None
        region, director, genre = None, None, None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, **more)
        entries.append(movie)

    return entries, next_url


def parse_tmdb_page_detail(page, **kwargs):
    base_url = kwargs["base_url"].rstrip("/") + "/"

    soup = BeautifulSoup(page, "html5lib")
    logging.info("Process movie = {}".format(strip(soup.title.text)))

    main_part = soup.body.main
    # part1 = main_part.find(class_="header")
    part1 = main_part.find(id="original_header")
    part2 = main_part.find(id="media_v4")

    img_part = part1.find(class_="poster")
    alt = img_part.img["alt"]
    img = base_url + img_part.img["src"]

    head_part = part1.find(class_="header poster")
    title_part = head_part.find(class_="title")
    href = strip(title_part.h2.a["href"])
    link = base_url + href
    title = strip(title_part.h2.a.text)
    year = extract_year(title_part.h2.find("span", class_="release_date").text)
    facts = title_part.find(class_="facts")
    rating = facts.find("span", class_="certification")
    if rating:
        rating = strip(rating.text)
    release_date = facts.find("span", class_="release")
    if release_date:
        release_date = strip(release_date.text)
    genre = facts.find("span", class_="genres")
    if genre:
        genre = strip(genre.text)
    length = facts.find("span", class_="runtime")
    if length:
        length = strip(length.text)
    score = strip(head_part.find("div", class_="user_score_chart")["data-percent"])
    header_info = head_part.find(class_="header_info")
    tagline = strip(header_info.h3.text)
    overview = strip(header_info.find(class_="overview").text)
    info1 = [[strip(li.find("p", class_="character").text), strip(li.p.text)] for li in
             header_info.find_all("li", class_="profile")]

    left_part = part2.find(class_="white_column")
    right_part = part2.find(class_="grey_column")
    facts = right_part.find("section", class_="facts")
    keywords = right_part.find("section", class_="keywords")
    social_links = facts.find(class_="social_links").a
    website = social_links["href"] if social_links else None
    plist = facts.find_all("p", recursive=False)
    info2 = []
    for p in plist:
        if not p.strong:
            continue
        key = p.strong.text
        p.strong.decompose()
        val = p.text
        info2.append([strip(key), strip(val)])

    keywords = [strip(li.text) for li in keywords.find_all("li")]
    left_part.find("section", class_="top_billed")
    cast_part = left_part.find("section", class_="top_billed").find_all("li")
    actors = [[strip(li.p.a.text), strip(li.find("p", class_="character").text)] for li in cast_part if
              li.find("p", class_="character")]
    review_part = left_part.find("section", class_="review").find_all("li")
    reviews = []
    for li in review_part:
        lia = li.a
        if not lia.span: continue
        val = lia.span.text
        lia.span.decompose()
        key = lia.text
        reviews.append([strip(key), strip(val)])
    media_part = left_part.find("section", class_="panel media_panel media scroller")
    if not media_part:
        media_part = left_part.find("section", class_='panel media_panel media tv_panel scroller')
    media_part = media_part.find_all("li")
    resources = []
    for li in media_part:
        lia = li.a
        if li and lia and lia.span:
            val = lia.span.text
            lia.span.decompose()
            key = lia.text
            resources.append([strip(key), strip(val)])

    extra = {
        "tmdb-cover": img,
        "tmdb-url": link,
        "tmdb-score": score,
        "tmdb-comment": tagline,
        "tmdb-summary": overview,
        "tmdb-titles": alt,
        "tmdb-release-date": release_date,
        "tmdb-length": length,
        "tmdb-rating": rating,
        "tmdb-website": website,
        "tmdb-info": info1 + info2,
        "tmdb-keywords": keywords,
        "tmdb-actors": actors,
        "tmdb-reviews": reviews,
        "tmdb-resources": resources,
    }
    tag = MovieTag.TMDB_DETAIL
    # category = "tv" if left_part.find("section", class_="panel season") else "movie"
    category = href.strip("/").split("/")[0].strip()  # tv or movie
    region = None
    director = []
    for k, v in info1:
        k = k.lower()
        if "director" in k or "creator" in k:
            director.append(v)
    movie = Movie(title, category, year, region, director, genre, tag=tag, **extra)
    return movie
