import datetime
import json
import logging
import re
import requests

from pathlib import Path
from curl_cffi import requests as requests_cffi
from fake_useragent import UserAgent


def get_page(request_option="requests", headers=None):
    url = "https://www.imdb.com/chart/top/"
    page_source = None

    if request_option == "selenium":
        pass
        # button_xpath = '//*[@id="list-view-option-detailed"]'
        # logging.info("use selenium")
        # chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument("--headless")
        # chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--disable-gpu")
        # chrome_options.add_argument("--disable-dev-shm-usage")
        # chrome_options.add_argument("user-agent=" + headers["User-agent"])
        # chrome_options.page_load_strategy = "eager"

        # logging.info("start")
        # driver = webdriver.Chrome(chrome_options)

        # logging.info("get url")
        # driver.get(url)
        # driver.implicitly_wait(15)
        # # time.sleep(5)

        # logging.info("click")
        # load_more_button = driver.find_element(By.XPATH, button_xpath)
        # load_more_button.click()
        # driver.implicitly_wait(15)

        # logging.info("scroll")
        # driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
        # driver.implicitly_wait(10)

        # logging.info("get page")
        # page_source = driver.page_source
        # driver.quit()
    else:
        if request_option == "curl_cffi":
            response = requests_cffi.get(url, impersonate="chrome110")
        else:
            response = requests.get(url, headers=headers)

        if response.status_code == 200:
            page_source = response.text

    return page_source


def parse_imdb_v4(file, source="file", total=250):
    tag1 = '<script id="__NEXT_DATA__" type="application/json">'
    tag2 = "</script>"
    pattern = rf"{tag1}.+?{tag2}"

    if source == "file":
        with open(file) as f:
            data = f.read()
    else:
        data = file

    out = re.findall(pattern, data)
    assert len(out) == 1

    json_data = json.loads(out[0].split(tag1)[-1].split(tag2)[0])
    items = json_data["props"]["pageProps"]["pageData"]["chartTitles"]["edges"]
    data = []
    if len(items) != total:
        logging.warning(f"error items count = {len(items)}/{total}")
        return data

    for item in items:
        node = item["node"]

        rank = str(int(item["currentRank"]))
        movie_id = node["id"]
        img_id = node["primaryImage"]["id"]
        video_id = node["latestTrailer"]["id"] if node["latestTrailer"] else ""

        link = f"https://www.imdb.com/title/{movie_id}/"
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
        data.append(entry)
    return data


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

    total = 250
    request_option = "requests"
    source = "text"

    top250_list = []
    logging.info("load page")
    page = get_page(request_option, headers=headers)

    logging.info("parse page")
    if page:
        top250_list = parse_imdb_v4(page, source=source)

    if len(top250_list) == total:
        data = {
            "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "movies": top250_list,
        }

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
    process(filename="data/imdb-movie-top250.json")
