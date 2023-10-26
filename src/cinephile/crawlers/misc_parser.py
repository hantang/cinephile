import logging
import re

from bs4 import BeautifulSoup

from cinephile.utils.movies import Movie


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
    for item in items:
        td_list = item.find_all("td")
        rank = td_list[0].text.strip().rstrip(".")
        title = td_list[3].span.a.text.strip()
        year = int(td_list[3].span.span.text.strip("()"))
        score = td_list[2].text.strip()
        count = td_list[4].text.strip().replace(",", "")

        a = td_list[5].find_all("a")[-1]
        link = a["href"]
        extra = a.img["title"]
        extra_out = re.findall(r"position: (\d){1,3} \((\d\.?\d?) with (\d[\d,]+) votes\)", extra)
        img = None
        score = {
            "imdb-score": score,
            "imdb-vote": count,
        }
        more = {
            "imdb_id": link.rstrip("/").split("/")[-1],
        }
        if extra_out:
            more["new-imbd-rank"] = extra_out[0][0]
            more["new-imbd-score"] = extra_out[0][1]
            more["new-imbd-vote"] = extra_out[0][2].replace(",", "")
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
    return desc, entries
