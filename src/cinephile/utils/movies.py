from __future__ import annotations

import logging
from typing import List, Any, Union, Optional

import pandas as pd
from pendulum import DateTime

from cinephile.utils.datetimes import time2str


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

    def _get_score(self):
        out = {}
        score_dict = self.entry['score']
        for key in score_dict.keys():
            if 'score' in key:
                out[key] = score_dict[key]
        for key in ['douban', 'imdb']:
            if key in self.entry:
                sub_entry = self.entry[key]
                sub_score_dict = sub_entry['score']
                for key in sub_score_dict.keys():
                    if 'score' in key and key not in out:
                        out[key] = score_dict[key]
        return out

    def flatten2dict(self, score="all"):
        keys = ['title', 'type', 'link', 'img', 'year', 'rank']
        out = {k: self.entry[k] for k in keys}
        out_score_raw = self._get_score()
        out_score = {}
        if score == "all":
            out_score = out_score_raw
        elif score == "douban":
            out_score['douban-score'] = out_score_raw.get('douban-score')
        elif score == "imdb":
            out_score['imdb-score'] = out_score_raw.get('imdb-score')
        out.update(out_score)
        return out

    def flatten2mdstr(self, link=True, img=False, rank=False, emoji=True):
        # convert to markdown string
        emoji_dict = {
            "year": "🎬🗓️📅",
            "score": "🌟⭐✨❗",
            "rank": "🥇🥈🥉🏅",
        }

        item = self.flatten2dict()
        out = []  # img, title, (year, score, rank)
        if img and item['img']:
            out.append("![pic-{}]({})".format(item['title'], item['img']))

        if link and item["link"]:
            out.append("[{}]({})".format(item['title'], item['link']))
        else:
            out.append(item['title'])

        year_val, score_val, rank_val = "", "", ""
        if item['year']:
            year = str(item['year'])
            if emoji:
                year_val = emoji_dict['year'][0] + " " + year
        score = None
        if item.get('douban-score'):
            score = float(item['douban-score'])
            score = "{:.2f}".format(score) if score > 0 else ""
            score_val = "{} {}".format(emoji_dict['score'][0] if emoji else "", score).strip()
        elif item.get('imdb-score'):
            score = float(item['imdb-score'])
            score = "{:.2f}".format(score) if score > 0 else ""
            score_val = "{}{}".format(emoji_dict['score'][1] if emoji else "", score).strip()
        else:
            keys = [key for key in sorted(item.keys()) if '-score' in key]
            if keys:
                score = float(item[keys[0]])
                score = "{:.2f}".format(score) if score > 0 else ""
                score_val = "{}{}".format(emoji_dict['score'][2] if emoji else "", score).strip()
        if emoji and score_val == "":
            score_val = emoji_dict['score'][-1]

        if rank and item.get("rank"):
            rank_val = int(item.get("rank"))
            rank_emoji = emoji_dict['rank'][rank_val - 1] if rank_val <= 3 else emoji_dict['rank'][-1]
            rank_val = "{}{:03d}".format(rank_emoji if emoji else "", rank_val).strip()

        out.append("({})".format(" / ".join([year_val, score_val, rank_val])).strip("/").strip())
        return "<br>".join([v.strip() for v in out])

    def query(self, key):
        pass

    @classmethod
    def from_json(cls, json_data):
        title = json_data["title"]
        link = json_data['link']
        img = json_data['img']
        year = json_data['year']
        rank = json_data['rank']
        mtype = json_data["type"]
        score = json_data['score']
        douban, imdb = None, None
        more = json_data['extra']
        if 'douban' in json_data:
            douban = Movie.from_json(json_data['douban'])
        if "imdb" in json_data:
            imdb = Movie.from_json(json_data['imdb'])
        movie = cls(title, link, img, year, rank, mtype=mtype, score=score, douban=douban, imdb=imdb, **more)
        return movie


class MovieCluster:
    def __init__(
            self,
            release_time: Union[str, DateTime],
            update_time: Union[str, DateTime],
            description: str,
            source: Union[str, List[str]],
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
        keys = ['release_time', 'update_time', 'description', 'source', 'movie_total', 'cluster_total',
                'movie', 'movies', 'cluster', 'draft']
        movie, movies, cluster = None, None, None

        release_time = json_data['release_time']
        update_time = json_data['update_time']
        description = json_data['description']
        source = json_data['source']
        draft = json_data.get("draft")
        more = {k: v for k, v in json_data.items() if k not in keys}

        if 'movie' in json_data:
            movie = Movie.from_json(json_data['movie'])
        if 'movies' in json_data:
            movies = [Movie.from_json(movie_data) for movie_data in json_data['movies']]
        if "cluster" in json_data:
            cluster = [MovieCluster.from_json(cluster_data) for cluster_data in json_data['cluster']]

        movie_cluster = MovieCluster(release_time, update_time, description, source, movie=movie, movies=movies,
                                     cluster=cluster, draft=draft, **more)
        return movie_cluster

    def get_movie(self) -> Optional[Movie]:
        return self.collection.get("movie")

    def get_movies(self) -> Optional[List[Movie]]:
        return self.collection.get("movies", [])

    def get_cluster(self) -> Optional[List[MovieCluster]]:
        return self.collection.get("cluster", [])

    def to_df(self, link=False, img=False):
        cluster = self.get_cluster()
        if not cluster:
            return None

        n = len(cluster)
        if isinstance(link, list):
            links = [True if i in link else False for i in range(n)]
        else:
            links = [link] * n
        if isinstance(img, list):
            imgs = [True if i in img else False for i in range(n)]
        else:
            imgs = [img] * n
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
            cols = [m.flatten2mdstr(link=links[i], img=imgs[i], rank=True) for m in movies]

            table[desc] = cols
        df = pd.DataFrame.from_dict(table, orient='index').T
        return df
