import datetime
import json
import logging
# import requests

from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from curl_cffi import requests


url_pattern = "https://movie.douban.com/top250?start={}&filter="
info_keys = ["director", "actor", "year", "region", "genre"]


def strip(text):
    return text.strip().lstrip("/").strip()


def crawler(url, headers, nums):
    entries = []
    # response = requests.get(url, headers=headers)
    response = requests.get(url, impersonate="chrome110")
    if response.status_code != 200:
        logging.warning(f"error requests: status={response.status_code}, url={url}")
        return entries

    soup = BeautifulSoup(response.text, "html.parser")
    grid_view_list = soup.body.find(id="content").find_all("ol", class_="grid_view")
    for grid_view in grid_view_list:
        for item in grid_view.find_all("li"):
            rank = item.select_one(".pic em").text
            img = item.select_one(".pic img")["src"]
            link = item.select_one(".info .hd a")["href"]
            titles = [strip(title.text) for title in item.select(".info .hd .title")]
            info = strip(item.select_one(".info .bd p").text)
            info_values = [
                strip(v)
                for val in info.split("\n")
                for v in val.strip().split("\xa0")
                if len(strip(v)) > 0
            ]
            star = item.select_one(".info .bd .star")
            star_score = star.select_one(".rating_num").text
            star_count = star.find_all("span")[-1].text
            quote = item.select_one(".info .bd .quote")
            quote = quote.text.strip() if quote else ""

            entry = {
                "rank": rank,
                "cover": img,
                "link": link,
                "title": titles,
                "info": dict(zip(info_keys, info_values)),
                "star": {"score": star_score, "count": star_count.split("人")[0]},
                "quote": quote,
            }
            entries.append(entry)

    if len(entries) != nums:
        logging.warning(f"error nums: {len(entries)}/{nums}")
    return entries


def process(filename):
    ua = UserAgent()
    headers = {"User-agent": ua.chrome}
    logging.info(f"start, headers={headers}")
    
    top250_list = []
    interval = 25
    total = 250
    for num in range(0, total, interval):
        url = url_pattern.format(num)
        if num == 0:
            url = url.split("?")[0]
        logging.info(f"{num}/{len(top250_list)}, next url={url}")
        out = crawler(url, headers, interval)
        top250_list.extend(out)
    
    dt = datetime.datetime.utcnow()
    if len(top250_list) == total:
        data = {
            "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "movies": top250_list,
        }
        filename = "{}-v{}.json".format(filename.split(".")[0], dt.strftime("%Y%m%d"))
        logging.info(f"save to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        logging.warning(f"error of top250_list: {len(top250_list)}/{total}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s",
    )
    process(filename="data/douban-movie-top250.json")
