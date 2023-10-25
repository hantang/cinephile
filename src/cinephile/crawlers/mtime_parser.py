import logging
from typing import List, Optional

from cinephile.utils.movies import Movie

mtime_id_year_map = {
    "68615": "1978",
    "90353": "2006",
    "90360": "2004",
    "209905": "2011",
    "67899": "2000",
    "99148": "2005",
    "114504": "2009",
    "123108": "2009",
    "133561": "2010",
    "222038": "2015",
    "42363": "1959",
    "42370": "1959",
    "44348": "1954",
    "46208": "1980",
    "47971": "1989",
    "56144": "1959",
    "92966": "1999",
    "105560": "1981",
    "105652": "2009",
    "10945": "1956",
    "29813": "1993",
    "46567": "1981",
    "48155": "1988",
    "48280": "1988",
    "48350": "1982",
    "48645": "1983",
    "54520": "1963",
    "99689": "2008",
    "112891": "2009",
    "13895": "1949",
    "16253": "1949",
    "86714": "1990",
    "95026": "2001",
    "217412": "2014",
    "72917": "2007",
    "58032": "2007",
    "132281": "2009",
}


def parse_mtime_json_top(page: dict, **kwargs) -> Optional[List[Movie]]:
    # 时光电影Top100，华语电影...
    order = kwargs.get("order")
    tops = page["data"]["movieTopList"]["topListInfos"]
    if order is None or order < 0 or order >= len(tops):
        logging.warning(f"Error params: order = {order}")
        return None

    draft = tops[order]
    items = draft["items"]
    movies = []
    for item in items:
        info = item["movieInfo"]
        rank = item["rank"]
        # title = item["title"]
        link = "http://movie.mtime.com/{}".format(info["movieId"])
        img = info["img"]
        mtime_id = str(info["movieId"])
        if info["releaseDate"]:
            year = int(info["releaseDate"][:4])
        elif mtime_id in mtime_id_year_map:
            year = int(mtime_id_year_map[mtime_id])
            # title = title.replace("(0)", f"({year})")
        else:
            year = 0
        title = info["movieName"]
        score = {"mtime-score": info["score"]}
        more = {
            "mtime_id": info["movieId"],
            "title-more": [info["movieName"], info["movieNameEn"], item["title"]],
            "director": info["director"],
            "actor": info["actors"],
            "date": info["releaseDate"],
            "region": info["releaseLocation"],
            "summary": item["description"],
            "award": info["award"],
        }
        movie = Movie(
            title,
            link,
            img,
            year,
            rank,
            mtype=None,
            score=score,
            **more,
        )
        movies.append(movie)
    return movies


def parse_mtime_json_detail(page: dict, **kwargs) -> Movie:
    """
    # http://front-gateway.mtime.com/library/movie/detail.api?tt=1698116020511&movieId=272641&locationId=290
    http://front-gateway.mtime.com/library/movie/detail.api?tt={}&movieId={}&locationId=290
    """
    item = page["data"]["basic"]
    title = item["name"]
    link = item["url"]
    img = item["img"]
    year = int(item["year"])
    score = {
        "mtime-score": item["overallRating"],
        "mtime-subsore": item["movieSubItemRatings"],
        "mtime-weight": item["ratingCountRatios"],
    }
    genre = item["type"]
    if not genre:
        genre = [v["name"] for v in item["movieGenres"]]
    date = item["releaseDateNew"] if item["releaseDateNew"] else item["releaseDate"]
    more = {
        "mtime_id": item["movieId"],
        "title-more": [item["name"], item["nameEn"]] + item["otherTitles"],
        "director": [v["name"] for v in item["directors"]],
        "writer": [v["name"] for v in item["writers"]],
        "actor": [v["name"] for v in item["actors"]],
        "date": date,
        "genre": genre,
        "region": item["releaseArea"],
        "summary": item["story"],
        "award": item["award"]["awardList"],
        "length": item["mins"],
    }
    movie = Movie(
        title,
        link,
        img,
        year,
        rank=None,
        mtype=None,
        score=score,
        **more,
    )
    return movie
