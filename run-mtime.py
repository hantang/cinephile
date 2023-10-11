import datetime
import json
import logging
import requests
import re
import time
from pathlib import Path
from curl_cffi import requests as requests_cffi
from fake_useragent import UserAgent


def get_page(request_option="requests", headers=None):
    # url = "http://www.mtime.com/top/movie/top100/indx-{}.html"
    # url = 'http://list.mtime.com/listIndex'
    url = 'http://front-gateway.mtime.com/library/index/app/topList.api?tt={}&'
    json_data = None

    timestamp = int(round(time.time() * 1000))
    url = url.format(timestamp)
    if request_option == "curl_cffi":
        response = requests_cffi.get(url, impersonate="chrome110")
    else:
        response = requests.get(url, headers=headers)

    if response.status_code == 200:
        json_data = response.json()

    return json_data



def process(filename, overwrite=False, request_option="requests"):
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

    json_data = get_page(request_option, headers=headers)
    if json_data:
        movieList = json_data['data']['movieTopList']['topListInfos']
        movieCnt = len(movieList[0]['items'])
        logging.info(f"Top movies = {movieCnt}")
        assert  movieCnt > 0
        
        data = {
            "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "movieList": movieList
        }
        logging.info(f"save to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        logging.warning(f"error of json data")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s",
    )
    process(filename="data/mtime-movie-top100.json")
