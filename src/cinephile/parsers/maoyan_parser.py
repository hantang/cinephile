import logging

from cinephile.utils.movies import Movie, MovieTag


def parse_maoyan_json_top(page, **kwargs):
    base_url = kwargs["base_url"].rstrip("/")
    items = page["data"]["movies"]
    entries = []
    tag = MovieTag.MAOYAN_TOP
    for item in items:
        title = item["nm"]
        rank = item["rank"]
        img = item["img"]
        maoyan_id = item["id"]
        link = f"{base_url}/films/{maoyan_id}"
        year = item["pubDesc"][:4]
        if year.isdigit():
            year = int(year)
        else:
            logging.warning(f"Error year {title}: {year}")
            year = 0
        more = {
            "maoyan-url": link,
            "maoyan-cover": img,
            "maoyan-id": maoyan_id,
            "maoyan-score": item["sc"],
            "maoyan-actor": item["star"],
            "maoyan-date": item["pubDesc"],
            "maoyan-watch-wish": item["wish"],
            "maoyan-summary": item["shortDec"],
        }
        category = None
        genre = item["cat"]
        region, director = None, None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, **more)
        entries.append(movie)
    return items, entries
