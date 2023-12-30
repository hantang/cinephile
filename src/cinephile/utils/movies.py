from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Any, Union, Optional

import pandas as pd
from pendulum import DateTime

from cinephile.utils.datetimes import time2str


class MovieTag(Enum):
    UNK = "unk"

    DOUBAN_TOP250 = "douban-top250"
    DOUBAN_LIST = "douban-doulist"
    DOUBAN_DETAIL = "douban-detail"
    DOUBAN_HOT = "douban-hot-list"
    DOUBAN_ANNUAL = "douban-annual-list"

    IMDB_TOP250 = "imdb-top250"
    IMDB_LIST = "imdb-list"
    IMDB_DETAIL = "imdb-detail"
    IMDB_TOP250_HIST = "imdb-top250-hist"

    MTIME_TOP = "mtime-top"
    MTIE_DETAIL = "mtime-detail"
    MAOYAN_TOP = "maoyan-top"
    TMDB_TOP = "tmdb-top"
    LC_LIST = "listchallenges(rottentomatoes)"


def _format_field(text):
    if text:
        if isinstance(text, list):
            return " / ".join([str(v).strip() for v in text])
        return text.strip()
    return None


class BaseMovie(ABC):
    keys_base = ["title",
                 "category",
                 "year",
                 "region",
                 "director",
                 "genre", ]
    keys_extra = "extra"

    def __init__(self,
                 title: Optional[str],
                 category: Optional[str] = None,
                 year: Optional[int] = 0,
                 region: Optional[str] = None,
                 director: Optional[str] = None,
                 genre: Optional[str] = None,
                 **kwargs
                 ):
        title = _format_field(title)
        region = _format_field(region)
        director = _format_field(director)
        genre = _format_field(genre)

        if category is None:
            category = "movie"

        assert category in ["movie", "tv", "other"]
        self._title = title
        self._category = category
        self._year = year
        self._region = region
        self._director = director
        self._genre = genre
        self._extra = kwargs

    @property
    def title(self):
        return self._title

    @property
    def category(self):
        return self._category

    @property
    def year(self):
        return self._year

    @property
    def region(self):
        return self._region

    @property
    def director(self):
        return self._director

    @property
    def genre(self):
        return self._genre

    @property
    def extra(self):
        return self._extra

    @abstractmethod
    def to_dict(self):
        out = {
            "title": self._title,
            "category": self._category,
            "year": self._year,
            "region": self._region,
            "director": self._director,
            "genre": self._genre,
        }
        return out

    @classmethod
    @abstractmethod
    def from_json(cls, json_data):
        pass


class DoubanMovie(BaseMovie):
    """对应豆瓣电影详情页信息
    """
    keys_douban = [
        "douban_url",
        "douban_cover",
        "douban_rank",
        "douban_id",
        "writers",
        "actors",
        "languages",
        "release_date",
        "websites",
        "length",
        "title_alias",
        "imdb_id",
        "score",
        "score_count",
        "score_weights",
        "summary",
        "resources",
        "rewards",
        "comments",
        "reviews",
        "discussion",
        "question",
        "watching"
    ]

    def __init__(self,
                 title,
                 category,
                 year,
                 region,
                 director,
                 genre,
                 douban_url,
                 douban_cover,
                 douban_rank,
                 douban_id,
                 writers,
                 actors,
                 languages,
                 release_date,
                 websites,
                 length,
                 title_alias,
                 imdb_id,
                 score,
                 score_count,
                 score_weights,
                 summary,
                 resources,
                 rewards,
                 comments,
                 reviews,
                 discussion,
                 question,
                 watching,
                 **kwargs):
        super().__init__(title, category, year, region, director, genre, **kwargs)
        self._douban_url = douban_url
        self._douban_cover = douban_cover
        self._douban_rank = douban_rank
        self._douban_id = douban_id

        self._writers = writers
        self._actors = actors
        self._languages = languages
        self._release_date = release_date
        self._websites = websites
        self._length = length
        self._title_alias = title_alias
        self._imdb_id = imdb_id
        self._score = score
        self._score_count = score_count
        self._score_weights = score_weights
        self._summary = summary
        self._resources = resources
        self._rewards = rewards
        self._comments = comments
        self._reviews = reviews
        self._discussion = discussion
        self._question = question
        self._watching = watching

    @property
    def score(self):
        return self._score

    @property
    def douban_id(self):
        return self._douban_id

    @property
    def douban_rank(self):
        return self._douban_rank

    @property
    def douban_url(self):
        return self._douban_url

    @property
    def douban_cover(self):
        return self._douban_cover

    def to_dict(self):
        out = super().to_dict()
        out.update({
            "douban_url": self._douban_url,
            "douban_cover": self._douban_cover,
            "douban_rank": self._douban_rank,
            "douban_id": self._douban_id,
            "writers": self._writers,
            "actors": self._actors,
            "languages": self._languages,
            "release_date": self._release_date,
            "websites": self._websites,
            "length": self._length,
            "title_alias": self._title_alias,
            "imdb_id": self._imdb_id,
            "score": self._score,
            "score_count": self._score_count,
            "score_weights": self._score_weights,
            "summary": self._summary,
            "resources": self._resources,
            "rewards": self._rewards,
            "comments": self._comments,
            "reviews": self._reviews,
            "discussion": self._discussion,
            "question": self._question,
            "watching": self._watching,
        })
        out["extra"] = self._extra
        return out

    @classmethod
    def from_json(cls, json_data):
        keys = cls.keys_base + cls.keys_douban
        params = {k: json_data.get(k) for k in keys}
        params.update(json_data.get(cls.keys_extra))
        movie = cls(**params)
        return movie


class ImdbMovie(BaseMovie):
    keys_imdb = ["imdb_url",
                 "imdb_cover",
                 "imdb_rank",
                 "imdb_id",
                 "writers",
                 "actors",
                 "languages",
                 "release_date",
                 "websites",
                 "length",
                 "title_alias",
                 "title_orig",
                 "score",
                 "score_count",
                 "metascore",
                 "rating",
                 "summary",
                 "resources",
                 "rewards",
                 "reviews",
                 "question", ]

    def __init__(self,
                 title,
                 category,
                 year,
                 region,
                 director,
                 genre,
                 imdb_url,
                 imdb_cover,
                 imdb_rank,
                 imdb_id,
                 writers,
                 actors,
                 languages,
                 release_date,
                 websites,
                 length,
                 title_alias,
                 title_orig,
                 score,
                 score_count,
                 metascore,
                 rating,
                 summary,
                 resources,
                 rewards,
                 reviews,
                 question,
                 **kwargs):
        super().__init__(title, category, year, region, director, genre, **kwargs)
        self._imdb_url = imdb_url
        self._imdb_cover = imdb_cover
        self._imdb_rank = imdb_rank
        self._imdb_id = imdb_id

        self._writers = writers
        self._actors = actors
        self._languages = languages
        self._release_date = release_date
        self._websites = websites
        self._length = length
        self._title_alias = title_alias
        self._imdb_id = imdb_id
        self._score = score
        self._metascore = metascore
        self._score_count = score_count
        self._rating = rating
        self._summary = summary
        self._resources = resources
        self._rewards = rewards
        self._reviews = reviews
        self._question = question
        self._title_orig = title_orig

    @property
    def score(self):
        return self._score

    @property
    def metascore(self):
        return self._metascore

    @property
    def rating(self):
        return self._rating

    @property
    def imdb_id(self):
        return self._imdb_id

    @property
    def imdb_rank(self):
        return self._imdb_rank

    @property
    def imdb_url(self):
        return self._imdb_url

    @property
    def imdb_cover(self):
        return self._imdb_cover

    def to_dict(self):
        out = super().to_dict()
        out.update({"imdb_url": self._imdb_url,
                    "imdb_cover": self._imdb_cover,
                    "imdb_rank": self._imdb_rank,
                    "imdb_id": self._imdb_id,
                    "writers": self._writers,
                    "actors": self._actors,
                    "languages": self._languages,
                    "release_date": self._release_date,
                    "websites": self._websites,
                    "length": self._length,
                    "title_alias": self._title_alias,
                    "title_orig": self._title_orig,
                    "score": self._score,
                    "score_count": self._score_count,
                    "metascore": self._metascore,
                    "rating": self._rating,
                    "summary": self._summary,
                    "resources": self._resources,
                    "rewards": self._rewards,
                    "reviews": self._reviews,
                    "question": self._question, })
        out["extra"] = self.extra
        return out

    @classmethod
    def from_json(cls, json_data):
        keys = cls.keys_base + cls.keys_imdb
        params = {k: json_data.get(k) for k in keys}
        params.update(json_data.get(cls.keys_extra))
        movie = cls(**params)
        return movie


class Movie(BaseMovie):
    keys_more = ["tag", "rank", "douban_id", "imdb_id", "douban", "imdb"]
    keys_deprecate = ["type", "url", "link", "cover", "img"]

    def __init__(
            self,
            title: Optional[str],
            category: Optional[str] = None,
            year: Optional[int] = 0,
            region: Optional[str] = None,
            director: Optional[str | List] = None,
            genre: Optional[str] = None,
            tag: Optional[MovieTag] = None,
            rank: Optional[int] = 0,
            douban_id: Optional[str] = None,
            imdb_id: Optional[str] = None,
            douban: Optional[DoubanMovie] = None,
            imdb: Optional[ImdbMovie] = None,
            **kwargs,
    ):
        super().__init__(title, category, year, region, director, genre, **kwargs)
        self._tag = tag if tag else MovieTag.UNK
        self._rank = rank if rank else 0
        self._douban_id = douban.douban_id if douban else douban_id
        self._imdb_id = imdb.imdb_id if imdb else imdb_id
        self._douban = douban
        self._imdb = imdb

    def to_entry(self):
        # todo
        out = {
            "title": self._title,
            "category": self._category,
            "year": self._year,
            "region": self._region,
            "director": self.director,
            "genre": self._genre,
        }
        if self._douban_id and not self._douban:
            out["douban_id"] = self._douban_id
        elif self._douban:
            pass
        if self._imdb_id and not self._imdb:
            out["imdb_id"] = self._imdb_id
        elif self._imdb:
            pass
        # "douban_info": self._douban.to_dict() if self._douban else None,
        # "imdb": self._imdb.to_dict() if self._imdb else None,

    def to_dict(self) -> dict:
        out = super().to_dict()
        out.update({
            "tag": self._tag.value,
            "rank": self._rank,
            "douban_id": self._douban_id,
            "imdb_id": self._imdb_id,
            "douban": self._douban.to_dict() if self._douban else None,
            "imdb": self._imdb.to_dict() if self._imdb else None,
        })
        out["extra"] = self._extra
        return out

    @classmethod
    def from_json(cls, json_data):
        title = json_data["title"]
        category = json_data.get("category", json_data.get("type"))
        year = json_data["year"]
        region = json_data.get("region")
        director = json_data.get("director")
        genre = json_data.get("genre")

        douban, imdb = None, None
        douban_id = json_data.get("douban_id")
        imdb_id = json_data.get("imdb_id")

        if "douban" in json_data and json_data["douban"]:
            douban = DoubanMovie.from_json(json_data["douban"])
            douban_id = douban.douban_id
        if "imdb" in json_data and json_data["imdb"]:
            imdb = ImdbMovie.from_json(json_data["imdb"])
            imdb_id = imdb.imdb_id

        tag = MovieTag(json_data["tag"]) if "tag" in json_data else MovieTag.UNK
        rank = json_data.get("rank")

        url = json_data.get("url", json_data.get("link"))
        cover = json_data.get("cover", json_data.get("img"))
        more = json_data["extra"]
        if url:
            more["url"] = more["url"]
        if cover:
            more["cover"] = cover["cover"]
        all_keys = cls.keys_base + [cls.keys_extra] + cls.keys_more + cls.keys_deprecate
        for k, v in json_data.items():
            if k not in all_keys:
                more[k] = v
        movie = cls(title, category, year, region, director, genre, tag=tag, rank=rank, douban_id=douban_id,
                    imdb_id=imdb_id,
                    douban=douban, imdb=imdb, **more)
        return movie


class MovieCluster:
    def __init__(
            self,
            release_time: Union[str, DateTime],
            update_time: Union[str, DateTime],
            description: str,
            source: Union[str, List[str]] = None,
            movie: Optional[Movie] = None,
            movies: Optional[List[Movie]] = None,
            cluster: Optional[List[MovieCluster]] = None,
            draft: Any = None,
            **kwargs,
    ):
        self.release_time = time2str(update_time, 0) if isinstance(release_time, DateTime) else str(release_time)
        self.update_time = time2str(update_time, 1)
        self.source = source
        self.description = description
        self.movie = movie
        self.movies = movies
        self.cluster = cluster
        self.total = 0
        self.collection = {
            "release_time": self.release_time,
            "update_time": self.update_time,
            "description": self.description,
            "source": self.source,
            "movie_total": self.total,
            "cluster_total": 0,
        }
        for key, value in kwargs.items():
            self.collection[key] = value

        if self.movie:
            self.collection["movie"] = movie
            self.total += 1
        if self.movies:
            self.collection["movies"] = movies
            self.total += len(movies)
        if self.cluster:
            self.collection["cluster_total"] = len(cluster)
            self.collection["cluster"] = cluster
            self.total += sum([c.total for c in cluster])
        self.collection["movie_total"] = self.total

        if draft:
            self.collection["draft"] = draft

    def get_movie(self) -> Optional[Movie]:
        return self.collection.get("movie")

    def get_movies(self) -> Optional[List[Movie]]:
        return self.collection.get("movies", [])

    def get_cluster(self) -> Optional[List[MovieCluster]]:
        return self.collection.get("cluster", [])

    def to_dict(self) -> dict:
        out = {}
        for k, v in self.collection.items():
            if isinstance(v, Movie) or isinstance(v, MovieCluster):
                out[k] = v.to_dict()
            elif (v and isinstance(v, list)
                  and (isinstance(v[0], Movie) or isinstance(v[0], MovieCluster))):
                out[k] = [v0.to_dict() for v0 in v]
            else:
                out[k] = v
        return out

    @classmethod
    def from_json(cls, json_data):
        # todo json data covert into Movie
        keys = ["release_time", "update_time", "description", "source", "movie_total", "cluster_total",
                "movie", "movies", "cluster", "draft"]
        movie, movies, cluster = None, None, None

        release_time = json_data["release_time"]
        update_time = json_data["update_time"]
        description = json_data["description"]
        source = json_data["source"]
        draft = json_data.get("draft")
        more = {k: v for k, v in json_data.items() if k not in keys}

        if "movie" in json_data:
            movie = Movie.from_json(json_data["movie"])
        if "movies" in json_data:
            movies = [Movie.from_json(movie_data) for movie_data in json_data["movies"]]
        if "cluster" in json_data:
            cluster = [MovieCluster.from_json(cluster_data) for cluster_data in json_data["cluster"]]

        movie_cluster = MovieCluster(release_time, update_time, description, source, movie=movie, movies=movies,
                                     cluster=cluster, draft=draft, **more)
        return movie_cluster

    def to_df(self, link=False, img=False, export=None):  # TODO
        cluster = self.get_cluster()
        if not cluster:
            return None

        n = len(cluster)
        #     if isinstance(link, list):
        #         links = [True if i in link else False for i in range(n)]
        #     else:
        #         links = [link] * n
        #     if isinstance(img, list):
        #         imgs = [True if i in img else False for i in range(n)]
        #     else:
        #         imgs = [img] * n
        logging.info(f"movies to df, cluster = {n}")
        table = {}
        for i, element in enumerate(cluster):
            desc = element.description
            movies = element.get_movies()
            logging.info(f"{desc}, movies = {len(movies)}")
            if movies is None or len(movies) == 0:
                logging.debug("try to get_cluster")
                clus = element.get_cluster()
                if clus:
                    # desc = clus[0].description
                    movies = clus[0].get_movies()
                elif element.get_movie():
                    logging.debug("try to get_movie")
                    movies = [element.get_movie()]
            # cols = [m.flatten2mdstr(link=links[i], img=imgs[i], rank=True) for m in movies]
            # todo
            cols = [m.to_entry() for m in movies]

            table[desc] = cols
        df = pd.DataFrame.from_dict(table, orient="index").T
        return df
