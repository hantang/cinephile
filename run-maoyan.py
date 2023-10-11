import datetime
import json
import logging
import requests
import hashlib
import random
import time

from bs4 import BeautifulSoup
from curl_cffi import requests as requests_cffi
from fake_useragent import UserAgent
from pathlib import Path



def get_url(offset, headers):
    url_base = "https://www.maoyan.com/board/4"
    parts = {
        "method": "GET",
        "timeStamp": str(int(time.time() * 1000)),
        "User-Agent": headers["User-agent"],
        "index": random.randint(1, 10),
        "channelId": 40011,
        "sVersion": 1,
        "signKey": None,
        "webdriver": "webdriver",
        "offset": offset,
    }

    # keys1 = ["method", "timeStamp", "User-Agent", "index", "channelId", "sVersion"]
    # keys2 = ["timeStamp", "channelId", "index", "signKey", "sVersion", "webdriver"]
    # if offset > 0:
    #     keys2 += ["offset"]
    # c = "&".join([f"{k}={parts[k]}" for k in keys1])
    # u= '&key=A013F70DB97834C0A5492378BD76C53A'
    # parts['signKey']=hashlib.md5((c+u).encode("utf-8")).hexdigest()
    # params = "&".join([f"{k}={parts[k]}" for k in keys2])
    # url = f"{url_base}?{params}"
    url = url_base
    if offset > 0:
        url += f"?offset={offset}"
    return url


def get_page(offset, request_option="requests", headers=None):
    url = get_url(offset, headers)
    # headers['cookie'] = ''
    page_source = None
    if request_option == "curl_cffi":
        response = requests_cffi.get(url, impersonate="chrome110")
    else:
        response = requests.get(url, headers=headers, params={"offset": offset})
    if response.status_code == 200:
        page_source = response.text
    else:
        logging.warning(f"Error, status={response.status_code}, url={url}")
    return page_source


def parse_v1(text):
    base = "https://www.maoyan.com"
    soup = BeautifulSoup(text, "html.parser")
    page_title = soup.title.text
    if page_title == "猫眼验证中心":
        print(page_title)
        return None, None

    nfb = soup.find("div", class_="not-found-body")
    if nfb:
        print(nfb.text.strip())
        return None, None

    divMain = soup.body.find("div", class_="main")
    updateTime = divMain.find("p", class_="update-time").text
    items = divMain.dl.find_all("dd")
    entries = []

    for item in items:
        rank = item.i.text
        img = item.find("img", class_="board-img")
        img = img["src"] if img.get("src") else img["data-src"]
        info = item.find("div", class_="movie-item-info")
        name = info.find("p", class_="name")
        link = base + name.a["href"]
        title = name.text
        actor = info.find("p", class_="star").text.strip()

        date = info.find("p", class_="releasetime").text.strip()
        parts = date.split("：")[1].split("(")
        year = parts[0].split("-")[0]
        region = parts[1].rstrip(")") if len(parts) > 1 else ""
        score = item.find("div", class_="movie-item-number").text.strip()
        entry = {
            "rank": rank,
            "cover": img,
            "link": link,
            "title": [title],
            "info": {"actor": actor, "year": year, "date": date, "region": region},
            "star": {"score": score},
        }
        entries.append(entry)
    return entries, updateTime


def run_v1(headers, request_option="requests"):
    top_list = []
    updateTime = None
    for offset in range(0, 100, 10):
        logging.info(f"{offset}/{len(top_list)}")
        page = get_page(offset, request_option, headers)
        if page:
            data, utime = parse_v1(page)
            if data:
                top_list.extend(data)
            else:
                logging.warning("error of data")
            if updateTime is None:
                updateTime = utime
    return top_list, updateTime


def run_v2(headers):
    # url = 'https://i.maoyan.com/asgard/board?year=0&term=0&id=39'
    url = "https://i.maoyan.com/asgard/asgardapi/mmdb/movieboard/moviedetail/fixedboard/39.json?ci=1&year=0&term=0&limit=100"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logging.warning(f"Error, status={response.status_code}, url={url}")
        return [], None

    data = response.json()
    updateTime = datetime.datetime.fromtimestamp(int(data["data"]["created"]) // 1000)
    updateTime = updateTime.strftime("%Y-%m-%d")
    top_list = data["data"]["movies"]
    return top_list, updateTime


def process(filename, overwrite=False):
    ua = UserAgent()
    headers = {"User-agent": ua.random}
    dt = datetime.datetime.utcnow()
    filename = Path("{}-v{}.json".format(filename.split(".")[0], dt.strftime("%Y%m%d")))
    info = "\n\t".join(["", f"time={dt}", f"file={filename}", f"headers={headers}"])
    logging.info(f"start:{info}")

    if filename.exists() and not overwrite:
        logging.warning(f"file={filename} exists")
        return
    if not filename.parent.exists():
        filename.parent.mkdir(parents=True)

    top_list, updateTime = run_v2(headers)

    if top_list:
        logging.info(f"Top movies = {len(top_list)}")
        data = {
            "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "updatetime": updateTime,
            "movies": top_list,
        }

        logging.info(f"save to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        logging.warning(f"error of top250_list: {len(top_list)}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s",
    )
    process(filename="data/maoyan-movie-top100.json")
