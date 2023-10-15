import json
import logging
import re

from .base import BaseCrawler


def parse_imdb_v4(page_data, title_url, total):
    tag1 = '<script id="__NEXT_DATA__" type="application/json">'
    tag2 = "</script>"
    pattern = rf"{tag1}.+?{tag2}"

    out = re.findall(pattern, page_data)
    assert len(out) == 1

    json_data = json.loads(out[0].split(tag1)[-1].split(tag2)[0])
    items = json_data["props"]["pageProps"]["pageData"]["chartTitles"]["edges"]

    entries = []
    if len(items) != total:
        logging.warning(f"error items count = {len(items)}/{total}")
        return entries

    for item in items:
        node = item["node"]

        rank = str(int(item["currentRank"]))
        movie_id = node["id"]
        img_id = node["primaryImage"]["id"]
        video_id = node["latestTrailer"]["id"] if node["latestTrailer"] else ""

        link = f"{title_url}/{movie_id}/"
        title = node["titleText"]["text"]
        img = node["primaryImage"]["url"]
        year = node["releaseYear"]["year"]
        runtime = node["runtime"]["seconds"]
        rating = node["certificate"]["rating"] if node["certificate"] else ""
        genre = ",".join([v["genre"]["text"] for v in node["titleGenres"]["genres"]])

        score = str(node["ratingsSummary"]["aggregateRating"])
        count = str(node["ratingsSummary"]["voteCount"])
        outline = node["plot"]["plotText"]["plainText"]

        entry = {
            "rank": rank,
            "cover": img,
            "link": link,
            "title": [title],
            "id": {
                "movie_id": movie_id,
                "image_id": img_id,
                "video_id": video_id,
            },
            "info": {
                # "director": director,
                # "actor": actor,
                "year": year,
                # "region": "",
                "genre": genre,
                "runtime": {"seconds": runtime},
                "rating": rating,
            },
            "star": {
                "score": score,
                "count": count,
            },
            # "quote": "",
            "outline": outline,
        }
        entries.append(entry)
    return entries


class ImdbCrawler(BaseCrawler):
    def __init__(self, savedir, overwrite=False, request_option="requests"):
        super(ImdbCrawler, self).__init__(savedir, overwrite)
        self.sitename = "imdb"
        self.baseurl = "https://www.imdb.com/chart/top/"
        self.title_url = "https://www.imdb.com/title"
        self.params = ""
        self.page_start = 0
        self.page_end = 1
        self.page_interval = 250
        self.total_items = self.page_interval * self.page_end
        self.request_option = request_option
        self.init_save()

    def get_url(self, param):
        return self.baseurl

    def get_page(self, url):
        if self.request_option == "requests":
            response = self.get_page_by_requests(url)
        else:
            response = self.get_page_by_curl_cffi(url)

        if response:
            return response.text

        logging.warning(f"response is null")
        return None

    def parse_page(self, page):
        entries = parse_imdb_v4(page, self.title_url, total=self.total_items)
        return entries

    def process(self):
        if self.check() and not self.overwrite:
            return -2
        url = self.get_url(None)
        logging.info(f"crawl num={self.page_end}, url = {url}")

        page = self.get_page(url)
        if not page:
            return -1
        logging.info(f"parse page, page={len(page)}")

        top_list = self.parse_page(page)
        logging.info(f"save to data, top_list = {len(top_list)}")
        self.save(top_list)
        return len(top_list)
