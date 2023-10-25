import re
import json

from bs4 import BeautifulSoup
import logging

from cinephile.utils.movies import Movie
from cinephile.utils.texts import strip, extract_year


def extract_imdb_page_info(page, desc=None):
    # 获取IMDB豆列信息和对应下载页面列表。
    logging.info("extract paginator: {} ...".format(desc if desc else ""))
    soup = BeautifulSoup(page, "html5lib")
    logging.info("Title = {}".format(strip(soup.title.text)))

    div_main = soup.body.find(id="main")
    name = div_main.h1.text.strip()
    author = strip(div_main.find(id="list-overview-summary").text)
    list_desc = {"name": name, "author": author, }
    # 总数
    # pagi = div_main.find(class_="list-pagination")
    # pagi.find(class_="next-page")["href"]
    # total = int(pagi.find(class_="pagination-range").text.strip().split("of")[-1])
    total_num = div_main.find(class_="desc lister-total-num-results").text.strip()
    total_num = int(total_num.split()[0].replace(",", ""))

    return total_num, list_desc


def parse_imdb_page_top_v4(page, **kwargs):
    total = kwargs["total"]
    base_url = kwargs["base_url"]

    tag1 = '<script id="__NEXT_DATA__" type="application/json">'
    tag2 = "</script>"
    pattern = rf"{tag1}.+?{tag2}"

    out = re.findall(pattern, page)
    if len(out) != 1:
        logging.error(f"parse error of pattern = {pattern}")
        return None

    json_data = json.loads(out[0].split(tag1)[-1].split(tag2)[0])
    items = json_data["props"]["pageProps"]["pageData"]["chartTitles"]["edges"]

    if len(items) != total:
        logging.warning(f"error items count = {len(items)}/{total}")

    entries = []
    for item in items:
        node = item["node"]

        rank = str(int(item["currentRank"]))
        movie_id = node["id"]
        img_id = node["primaryImage"]["id"]
        video_id = node["latestTrailer"]["id"] if node["latestTrailer"] else ""

        link = f"{base_url}/{movie_id}/"
        title = node["titleText"]["text"]
        img = node["primaryImage"]["url"]
        year = int(str(node["releaseYear"]["year"])[:4])
        runtime = node["runtime"]["seconds"]
        rating = node["certificate"]["rating"] if node["certificate"] else ""
        genre = ",".join([v["genre"]["text"] for v in node["titleGenres"]["genres"]])

        score = str(node["ratingsSummary"]["aggregateRating"])
        count = str(node["ratingsSummary"]["voteCount"])
        outline = node["plot"]["plotText"]["plainText"]

        score = {
            "imdb-score": score,
            "imdb-vote": count,
        }
        more = {
            "imdb-id": movie_id,
            "image-img-id": img_id,
            "video-video-id": video_id,
            "genre": genre,
            "rating": rating,
            "length": runtime,
            "summary": outline,
        }
        movie = Movie(title, link, img, year, rank, mtype=None, score=score, **more)
        entries.append(movie)
    return entries


def parse_imdb_page_list(page, **kwargs):
    # IMDb电影单解析
    base_url = kwargs["base_url"]
    soup = BeautifulSoup(page, "html5lib")
    div_main = soup.body.find(id="main")
    if not div_main:
        return None, None

    div_pagi = div_main.find("div", class_="list-pagination")
    next_url = div_pagi.find(class_="next-page")
    if next_url:
        next_url = next_url["href"]
    logging.info(f"next url = {next_url}")

    div_lister = div_main.find("div", class_="lister-list")
    items = div_lister.find_all(class_="lister-item mode-detail")
    logging.debug(f"items = {len(items)}")
    entries = []
    for item in items:
        t = item.find(class_="lister-item-image ribbonize")
        link = base_url + t.a["href"].split("?")[0]
        img = t.img["src"]

        t2 = item.find(class_="lister-item-content")
        idx = t2.h3.find(class_="lister-item-index").text.strip(".")
        title = t2.h3.a.text.strip()
        year = 0
        year_span = t2.h3.find("span", class_="lister-item-year")
        if year_span:
            year_out = extract_year(year_span.text.strip())
            if year_out:
                year = int(year_out[-1][0])

        score = strip(item.find(class_="ipl-rating-star small").text)
        t3 = item.find(class_="inline-block ratings-metascore")
        metascore = strip(t3.text) if t3 else ""
        extra = [strip(v.text) for v in item.find_all("p")]
        score = {
            "imdb-score": score,
            # "imdb-vote": count,
            "metascore": metascore
        }
        more = {
            "imdb-info": extra
        }
        movie = Movie(title, link, img, year, rank=idx, mtype=None, score=score, **more)
        entries.append(movie)
    return entries, next_url
