import logging
from typing import List, Optional

from cinephile.utils.movies import Movie, MovieTag

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
    tag = MovieTag.MTIME_TOP
    for item in items:
        info = item["movieInfo"]
        mtime_id = str(info["movieId"])
        rank = item["rank"]
        if info["releaseDate"]:
            year = int(info["releaseDate"][:4])
        elif mtime_id in mtime_id_year_map:
            year = int(mtime_id_year_map[mtime_id])
        else:
            year = 0
        title = info["movieName"]
        more = {
            "mtime_url": f"http://movie.mtime.com/{mtime_id}",
            "mtime_cover": info["img"],
            "mtime_id": info["movieId"],
            "mtime_score": info["score"],
            "mtime_title": [info["movieName"], info["movieNameEn"], item["title"]],
            "mtime_actor": info["actors"],
            "mtime_date": info["releaseDate"],
            "mtime_summary": item["description"],
            "mtime_award": info["award"],
        }
        director = info["director"]
        region = info["releaseLocation"]
        category = None
        genre = None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, **more)
        movies.append(movie)
    return movies


def parse_mtime_json_detail(page: dict, **kwargs) -> Movie:
    """
    # http://front-gateway.mtime.com/library/movie/detail.api?tt=1698116020511&movieId=272641&locationId=290
    http://front-gateway.mtime.com/library/movie/detail.api?tt={}&movieId={}&locationId=290
    """
    item = page["data"]["basic"]
    title = item["name"]
    year = int(item["year"])
    genre = item["type"]
    if not genre:
        genre = [v["name"] for v in item["movieGenres"]]
    date = item["releaseDateNew"] if item["releaseDateNew"] else item["releaseDate"]
    more = {
        "mtime_url": item["url"],
        "mtime_cover": item["img"],
        "mtime_id": item["movieId"],
        "mtime_score": item["overallRating"],
        "mtime_subsore": item["movieSubItemRatings"],
        "mtime_weight": item["ratingCountRatios"],
        "mtimes_titles": [item["name"], item["nameEn"]] + item["otherTitles"],
        "mtime_writer": [v["name"] for v in item["writers"]],
        "mtime_actor": [v["name"] for v in item["actors"]],
        "mtime_date": date,
        "mtime_summary": item["story"],
        "mtime_award": item["award"]["awardList"],
        "mtime_length": item["mins"],
    }
    director = [v["name"] for v in item["directors"]]
    region = item["releaseArea"]
    category = None
    tag = MovieTag.MTIE_DETAIL
    movie = Movie(title, category, year, region, director, genre, tag=tag, **more)
    return movie
