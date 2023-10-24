from __future__ import annotations

from typing import List, Any, Union, Optional

import pendulum

from cinephile.utils import datetimes


class Movie:
    def __init__(
        self,
        title: Optional[str],
        link: Optional[str],
        img: Optional[str],
        year: Optional[int],
        rank: Union[str, int] = None,
        mtype: Optional[str] = None,
        score: Optional[dict] = None,
        douban: Optional[Movie] = None,
        imdb: Optional[Movie] = None,
        **kwargs,
    ):
        self.title = title
        self.type = "movie"  # 电影/电视剧
        if mtype in ["电视", "电视剧", "剧集", "tv"]:
            self.type = "tv"
        elif mtype in ["电影", "movie", "film"]:
            self.mtype = "movie"

        self.link = link
        self.img = img
        self.year = int(year)
        self.rank = rank
        self.score = score
        self.more = kwargs
        self.entry = {
            "title": self.title,
            "type": self.type,
            "link": self.link,
            "img": self.img,
            "year": self.year,
            "rank": self.rank,
            "score": self.score,
        }
        if douban:
            self.entry["douban"] = douban
        if imdb:
            self.entry["imdb"] = imdb
        self._fill()

    def _fill(self):
        # todo parse values
        self.entry["extra"] = self.more

    def to_dict(self) -> dict:
        out = {
            k: v.to_dict() if isinstance(v, Movie) else v for k, v in self.entry.items()
        }
        return out

    def query(self, key):
        pass


class MovieCluster:
    def __init__(
        self,
        release_time: Union[str, pendulum.DateTime],
        update_time: Union[str, pendulum.DateTime],
        description: str,
        source: Union[str, List[str]],
        movie: Optional[Movie] = None,
        movies: Optional[List[Movie]] = None,
        cluster: Optional[List[MovieCluster]] = None,
        draft: Any = None,
        **kwargs,
    ):
        self.release_time = str(release_time)
        self.update_time = datetimes.time2str(update_time, 1)
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
        # todo limit keys
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

    def to_dict(self) -> dict:
        out = {}
        for k, v in self.collection.items():
            if isinstance(v, Movie) or isinstance(v, MovieCluster):
                out[k] = v.to_dict()
            elif (
                v
                and isinstance(v, list)
                and (isinstance(v[0], Movie) or isinstance(v[0], MovieCluster))
            ):
                out[k] = [v0.to_dict() for v0 in v]
            else:
                out[k] = v
        return out

    @classmethod
    def from_json(cls, json_data):
        # todo json data covert into Movie
        return cls(**json_data)

    def to_csv(self):
        pass

    def to_markdown(self):
        pass
