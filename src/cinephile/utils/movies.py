from __future__ import annotations

import logging
import math
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Any, Union, Optional

import pandas as pd
from pendulum import DateTime

from cinephile.utils.datetimes import time2str, now
from cinephile.utils.texts import strip_field


def _query(extra_dict, keys, default=None):
    keys = [k.lower() for k in keys]
    for key in keys:
        if key in extra_dict and extra_dict[key]:
            return extra_dict[key]
    for key in keys:
        for ek in extra_dict.keys():
            ek = ek.lower()
            if ek.endswith(key) and extra_dict[ek]:
                return extra_dict[ek]
    return default


def _fill_num(max_num):
    num = str(math.ceil(abs(max_num)))
    return len(num) if num[0] < "9" else len(num) + 1


def _flatten_data(data, default_key="", exclude_keys=None, fix_key=True):
    # 拉平嵌套的dict
    if fix_key:
        default_key = default_key.lower().replace("-", "_")
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            data2 = _flatten_data(v, k, exclude_keys, fix_key)
            for k2, v2 in data2.items():
                if exclude_keys and k2 in exclude_keys: continue
                out[k2] = v2
        return out
    else:
        return {default_key: data}


def _extra_num(num_str):
    if isinstance(num_str, int) or isinstance(num_str, float):
        return num_str
    elif isinstance(num_str, str):
        nums = re.findall(r"(\d+(\.\d*)?)", num_str)
        if nums:
            return nums[0][0]
        return 0.
    else:
        return 0.


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
    MAOYAN_DETAIL = "maoyan-detail"
    TMDB_TOP = "tmdb-top"
    TMDB_DETAIL = "tmdb-detail"
    LC_LIST = "listchallenges(rottentomatoes)"


class BaseMovie(ABC):
    keys_base = [
        "title",
        "category",
        "year",
        "region",
        "director",
        "genre",
    ]
    keys_extra = "extra"
    valid_tags = [mt.value for mt in list(MovieTag)]

    def __init__(self,
                 title: Optional[str],
                 category: Optional[str] = None,
                 year: Optional[int] = 0,
                 region: Optional[str] = None,
                 director: Optional[str] = None,
                 genre: Optional[str] = None,
                 **kwargs
                 ):
        title = strip_field(title)
        region = strip_field(region)
        director = strip_field(director)
        genre = strip_field(genre)

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
        "douban_score",
        "douban_vote",
        "douban_weights",
        "summary",
        "resources",
        "rewards",
        "comments",
        "reviews",
        "discussion",
        "question",
        "watching",
        "douban_playable"
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
                 douban_score,
                 douban_vote,
                 douban_weights,
                 summary,
                 resources,
                 rewards,
                 comments,
                 reviews,
                 discussion,
                 question,
                 watching,
                 douban_playable,
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
        self._douban_score = douban_score
        self._douban_vote = douban_vote
        self._douban_weights = douban_weights
        self._summary = summary
        self._resources = resources
        self._rewards = rewards
        self._comments = comments
        self._reviews = reviews
        self._discussion = discussion
        self._question = question
        self._watching = watching
        self._douban_playable = douban_playable

    @property
    def score(self):
        return self._douban_score

    @property
    def vote(self):
        return self._douban_vote

    @property
    def id(self):
        return self._douban_id

    @property
    def url(self):
        return self._douban_url

    @property
    def cover(self):
        return self._douban_cover
    
    @property
    def playable(self):
        return self._douban_playable

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
            "douban_score": self._douban_score,
            "douban_vote": self._douban_vote,
            "douban_weights": self._douban_weights,
            "summary": self._summary,
            "resources": self._resources,
            "rewards": self._rewards,
            "comments": self._comments,
            "reviews": self._reviews,
            "discussion": self._discussion,
            "question": self._question,
            "watching": self._watching,
            "douban_playable": self._douban_playable
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

    def to_entry(self):
        staff = " / ".join([v for v in [self._director, self._writers, self._actors] if v])
        out = {
            "douban_title": self._title,
            "douban_id": self._douban_id,
            "douban_url": self._douban_url,
            "douban_cover": self._douban_cover,
            "douban_score": self._douban_score,
            "douban_vote": self._douban_vote,
            "douban_weights": self._douban_weights,
            "douban_year": self._year,
            "douban_region": self._region,
            "douban_genre": self._genre,
            "douban_director": self._director,
            "douban_actor": self._actors,
            "douban_staff": staff,
            "douban_playable": self._douban_playable
        }
        return out


class ImdbMovie(BaseMovie):
    keys_imdb = [
        "imdb_url",
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
        "imdb_score",
        "imdb_vote",
        "metascore",
        "rating",
        "summary",
        "resources",
        "rewards",
        "reviews",
        "question",
    ]

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
                 imdb_score,
                 imdb_vote,
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
        self._imdb_score = imdb_score
        self._metascore = metascore
        self._imdb_vote = imdb_vote
        self._rating = rating
        self._summary = summary
        self._resources = resources
        self._rewards = rewards
        self._reviews = reviews
        self._question = question
        self._title_orig = title_orig

    @property
    def score(self):
        return self._imdb_score

    @property
    def vote(self):
        return self._imdb_vote

    @property
    def metascore(self):
        return self._metascore

    @property
    def id(self):
        return self._imdb_id

    @property
    def rank(self):
        return self._imdb_rank

    @property
    def url(self):
        return self._imdb_url

    @property
    def cover(self):
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
                    "imdb_score": self._imdb_score,
                    "imdb_vote": self._imdb_vote,
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

    def to_entry(self):
        staff = " / ".join([v for v in [self._director, self._writers, self._actors] if v])
        out = {
            "imdb_title": self._title,
            "imdb_id": self._imdb_id,
            "imdb_url": self._imdb_url,
            "imdb_cover": self._imdb_cover,
            "imdb_score": self._imdb_score,
            "imdb_vote": self._imdb_vote,
            "metascore": self._metascore,
            "imdb_year": self._year,
            "imdb_region": self._region,
            "imdb_genre": self._genre,
            "imdb_director": self._director,
            "imdb_actor": self._actors,
            "imdb_staff": staff,
        }
        return out


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
            **kwargs):
        super().__init__(title, category, year, region, director, genre, **kwargs)
        self._tag = tag if tag else MovieTag.UNK
        self._rank = rank if rank else 0
        self._douban_id = douban.douban_id if douban else douban_id
        self._imdb_id = imdb.imdb_id if imdb else imdb_id
        self._douban = douban
        self._imdb = imdb

    def to_entry(self):
        actors = _query(self._extra, ["actor", "actors", "staff"])
        staff = " / ".join([v for v in [self.director, actors] if v])
        score = _query(self._extra, ["score"])
        if score:
            if isinstance(score, dict):
                score = _query(score, ["score"])
        url = _query(self._extra, ["url", "link"])
        title_markdown = f"[{self._title}]({url})" if url and url.startswith("http") else self._title
        out = {
            "title": self._title,
            "category": self._category,
            "year": self._year,
            "region": self._region,
            "director": self.director,
            "genre": self._genre,
            "rank": self._rank,
            "tag": self._tag.value,
            "url": url,
            "title_markdown": title_markdown,
            "cover": _query(self._extra, ["cover", "img", "image"]),
            "staff": staff,
            "score": float(_extra_num(score)),

            "douban_id": self._douban_id,
            "douban_score": _query(self._extra, ["douban_score"]),
            "douban_vote": _query(self._extra, ["douban_vote", "douban_count"]),
            "imdb_id": self._imdb_id,
            "imdb_score": _query(self._extra, ["imdb_score"]),
            "imdb_vote": _query(self._extra, ["imdb_vote", "imdb_count"]),
        }

        if self._douban:
            out.update({
                "douban_id": self._douban.id,
                "douban_score": self._douban.score,
                "douban_vote": self._douban.vote,
            })
        if self._imdb:
            out.update({
                "imdb_id": self._imdb.id,
                "imdb_score": self._imdb.score,
                "imdb_vote": self._imdb.vote,
            })
        if out["douban_score"] and isinstance(out["douban_score"], str):
            out["douban_score"] = float(_extra_num(out["douban_score"]))
        if out["douban_vote"] and isinstance(out["douban_vote"], str):
            out["douban_vote"] = int(_extra_num(out["douban_vote"]))
        if out["imdb_score"] and isinstance(out["imdb_score"], str):
            out["imdb_score"] = float(_extra_num(out["imdb_score"]))
        if out["imdb_vote"] and isinstance(out["imdb_vote"], str):
            out["imdb_vote"] = int(_extra_num(out["imdb_vote"]))
        return out

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
        all_keys = cls.keys_base + [cls.keys_extra] + cls.keys_more + cls.keys_deprecate
        tmp_extra = {}
        for tmp_key in ["extra", "more", "movieInfo"]:
            if tmp_key not in json_data:
                continue
            for k, v in json_data[tmp_key].items():
                k = k.replace("-", "_").lower()
                tmp_extra[k] = v

        title = json_data.get("title", json_data.get("nm"))
        # assert title is not None
        category = json_data.get("category", json_data.get("type"))
        year = json_data.get("year", tmp_extra.get("year", 0))
        region = json_data.get("region", tmp_extra.get("region"))
        director = json_data.get("director", tmp_extra.get("director"))
        genre = json_data.get("genre", tmp_extra.get("genre"))
        rank = json_data.get("rank")

        douban, imdb = None, None
        douban_id = json_data.get("douban_id", tmp_extra.get("douban_id"))
        imdb_id = json_data.get("imdb_id", tmp_extra.get("imdb_id"))
        if "douban" in json_data and json_data["douban"]:
            douban = DoubanMovie.from_json(json_data["douban"])
            douban_id = douban.douban_id
        if "imdb" in json_data and json_data["imdb"]:
            imdb = ImdbMovie.from_json(json_data["imdb"])
            imdb_id = imdb.imdb_id

        tag_val = str(json_data.get("tag"))
        if tag_val and tag_val in cls.valid_tags:
            tag = MovieTag(tag_val)
        else:
            tag = MovieTag.UNK
        url = _query(json_data, ["url", "link"], default="")
        cover = _query(json_data, ["cover", "img", "image"], default="")
        url_key, cover_key = "url", "cover"
        if "douban" in url:
            url_key = f"douban_{url_key}"
        elif "imdb" in url:
            url_key = f"imdb_{url_key}"
        if "douban" in cover:
            cover_key = f"douban_{cover_key}"
        elif "amazon.com" in cover:
            cover_key = f"imdb_{cover_key}"

        if url_key == "douban_url" and not douban_id:
            douban_id = url.strip("/").split("/")[-1]
        if url_key == "imdb_url" and not imdb_id:
            imdb_id = url.strip("/").split("/")[-1]

        extra = {url_key: url, cover_key: cover}
        extra1 = _flatten_data(tmp_extra, exclude_keys=all_keys)
        extra2 = _flatten_data(json_data, exclude_keys=all_keys)
        extra.update(extra1)
        extra.update(extra2)

        movie = cls(title, category, year, region, director, genre, tag=tag, rank=rank,
                    douban_id=douban_id, imdb_id=imdb_id, douban=douban, imdb=imdb, **extra)
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

        release_time = json_data.get("release_time", json_data.get("datetime"))
        update_time = json_data.get("update_time", json_data.get("datetime"))
        description = json_data.get("description")
        source = json_data.get("source")
        draft = json_data.get("draft", json_data.get("more"))
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

    @classmethod
    def merge_from_json(cls, *json_data_list):
        release_time = now()
        update_time = release_time
        description = "merge"
        source = None
        cluster = [MovieCluster.from_json(json_data) for json_data in json_data_list]
        movie_cluster = MovieCluster(release_time, update_time, description, source, cluster=cluster)
        return movie_cluster

    def _to_movies(self) -> List:
        raw_cluster = self.get_cluster()
        raw_movies = self.get_movies()
        raw_movie = self.get_movie()
        movies_list = []
        if raw_cluster:
            for element in raw_cluster:
                description = element.description
                release_time = element.release_time
                raw_cluster2 = element.get_cluster()
                raw_movies2 = element.get_movies()
                raw_movie2 = element.get_movie()
                if raw_movies2:
                    movies_list.append((description, release_time, raw_movies2))
                elif raw_cluster2:
                    raw_movie3 = raw_cluster2[0].get_movies()
                    movies_list.append((description, release_time, raw_movie3))
                elif raw_movie2:
                    movies_list.append((description, release_time, [raw_movie2]))
        elif raw_movies:
            movies_list = [(self.description, self.release_time, raw_movies)]
        elif raw_movie:
            movies_list = [(self.description, self.release_time, [raw_movie])]

        if not movies_list:
            logging.warning("Movie list is empty, return nothing")
            return []
        return movies_list

    def to_df(self) -> pd.DataFrame:
        movies_list = self._to_movies()
        if not movies_list:
            return None
        table = []
        for movies_info in movies_list:
            (description, release_time, movies) = movies_info
            description_dict = {
                "description": description,
                "release_time": release_time
            }
            entries = [dict(**m.to_entry(), **description_dict) for m in movies]
            table.extend(entries)
        df = pd.DataFrame(table)
        return df

    def to_df_csv(self, keep_url=False) -> pd.DataFrame:
        """
        # Group 分榜	Rank 排名	Title 电影	Score 打分	Staff 人员	Region 地区	Genre 类型
        """
        movies_list = self._to_movies()
        if not movies_list:
            return None
        table = []
        for movies_info in movies_list:
            (description, release_time, movies) = movies_info
            desc = description.split(" | ")[0]
            movie_entries = [m.to_entry() for m in movies]
            for me in movie_entries:
                title = me["title"]
                if me["url"] and keep_url:
                    title = "[{}]({})".format(title, me["url"])
                me2 = {
                    "group": desc,
                    "rank": me["rank"],
                    "title": title,
                    "score": me["score"],
                    "staff": me["staff"],
                    "region": me["region"],
                    "genre": me["genre"],
                }
                table.append(me2)
            table.append({})
        if not table[-1]:
            table = table[:-1]

        df = pd.DataFrame(table)
        df = df.fillna(" ").astype(str)
        df["rank"] = df["rank"].apply(lambda x: x.split(".")[0])
        df["score"] = df["score"].apply(lambda x: "{:.2f}".format(float(x)) if x.replace(".", "").isdigit() else " ")

        names = ["Index", "Group 分榜", "Rank 排名", "Title 电影", "Score 打分", "Region 地区", "Genre 类型",
                 "Staff 人员"]
        cols = ["group", "rank", "title", "score", "region", "genre", "staff"]
        df2 = df[cols].reset_index()
        df2.columns = names
        return df2

    def to_df_table(self, keep_url=False, keep_cover=False, split_cover=False) -> pd.DataFrame:
        movies_list = self._to_movies()
        if not movies_list:
            return None

        metals = "🥇🥈🥉🏅"
        sep = "<br/>"
        n = len(movies_list)
        if isinstance(keep_url, list):
            keep_urls = keep_url[:n] + [False] * (n - len(keep_url))
        else:
            keep_urls = [keep_url] * n
        if isinstance(keep_cover, list):
            keep_covers = keep_cover[:n] + [False] * (n - len(keep_cover))
        else:
            keep_covers = [keep_cover] * n

        table = {}
        for i, movies_info in enumerate(movies_list):
            keep_url, keep_cover = keep_urls[i], keep_covers[i]
            (description, release_time, movies) = movies_info
            release_date = release_time.split(" ")[0].replace("-", "/")
            desc = sep.join([description, f"【📅{release_date}】"])

            movie_entries = [m.to_entry() for m in movies]
            ranks = [int(strip_field(e["rank"], 0)) for e in movie_entries]
            keep_rank = True if min(ranks) != max(ranks) and max(ranks) >= 1 else False
            num_len = max(_fill_num(max(ranks)), 1)

            cols = []
            for me in movie_entries:
                title = strip_field(me["title"], "")
                url = strip_field(me["url"], "")
                cover = strip_field(me["cover"], "")
                year = int(strip_field(me["year"], 0))
                score = float(strip_field(me["score"], 0))
                rank = int(strip_field(me["rank"], 0))
                rank_tag = metals[min(rank - 1, 3)]
                movie_id = strip_field(me.get("douban_id"), "")
                playable = strip_field(me.get("douban_playable"), "")

                headline = "[{}]({})".format(title, url) if keep_url else title
                if playable:
                    headline += f" `{playable}`"
                image = "![{}]({})".format(movie_id, cover) if keep_cover else ""
                info_parts = [f"🎬{year}" if year else "", f"🌟{score:.2f}" if score else ""]
                if keep_rank:
                    info_parts += [f"{rank_tag}{rank:0{num_len}d}" if rank else ""]
                info = " / ".join([v for v in info_parts if v])  # (🎬 2023 / 🌟 9.20 / 🥇001)
                if keep_cover and split_cover:
                    col = sep.join([v for v in [headline, f"({info})" if info else ""] if v])
                    cols.append(image)
                    cols.append(col)
                else:
                    col = sep.join([v for v in [image, headline, f"({info})" if info else ""] if v])
                    cols.append(col)
            table[desc] = cols
        df = pd.DataFrame.from_dict(table, orient="index").T
        df = df.fillna(" ").astype(str)
        return df
