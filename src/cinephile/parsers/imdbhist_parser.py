import logging
import re

from bs4 import BeautifulSoup

from cinephile.utils.movies import Movie, MovieTag
from cinephile.utils.texts import extract_year


def parse_imdb_hist_page_month(page, **kwargs):
    soup = BeautifulSoup(page)
    logging.info("Title = {}".format(soup.title.text.strip()))

    div_content = soup.body.find("div", id="content")
    desc = div_content.h1.text.strip()
    table = div_content.find("table", id="calendar-table")
    if not table:
        logging.warning("Error not found calendar-table")
        return None, None
    hrefs = [a["href"] for a in table.find_all("a")]
    logging.info(f"Found hrefs = {len(hrefs)}")
    return desc, hrefs


def parse_imdb_hist_page_date(page, **kwargs):
    soup = BeautifulSoup(page)
    logging.info("Title = {}".format(soup.title.text.strip()))

    div_content = soup.body.find("div", id="content")
    desc = div_content.h1.text.strip()

    sec_main = div_content.find(id="main")
    tables = sec_main.find_all("table", class_="list-data")
    if not tables:
        logging.info("Error")
        return None, None

    table = tables[-1]
    raw_items = table.find_all("tr")
    items = [item for item in raw_items if item.get("class") != ["tr-header"]]
    logging.info(f"items = {len(items)} / {len(raw_items)}")

    entries = []
    tag = MovieTag.IMDB_TOP250_HIST
    for item in items:
        td_list = item.find_all("td")
        rank = td_list[0].text.strip().rstrip(".")
        title = td_list[3].span.a.text.strip()
        year = extract_year(td_list[3].span.span.text)
        score = td_list[2].text.strip()
        count = td_list[4].text.strip().replace(",", "")

        a = td_list[5].find_all("a")[-1]
        link = a["href"]
        extra_out = re.findall(r"position: (\d){1,3} \((\d\.?\d?) with (\d[\d,]+) votes\)", a.img["title"])
        imdb_id = link.rstrip("/").split("/")[-1]
        more = {
            "imdb_score": score,
            "imdb_vote": count,
        }
        if extra_out:
            more["imdb-rank-new"] = extra_out[0][0]
            more["imdb-score-new"] = extra_out[0][1]
            more["imdb-vote-new"] = extra_out[0][2].replace(",", "")
        category = None
        region, director, genre = None, None, None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, imdb_id=imdb_id, **more)
        entries.append(movie)
    return desc, entries
