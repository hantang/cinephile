import hashlib
import logging
import random
import datetime
import re

from bs4 import BeautifulSoup

from cinephile.utils.movies import Movie, MovieTag
from cinephile.utils.texts import strip, extract_year


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
            "maoyan_url": link,
            "maoyan_cover": img,
            "maoyan_id": maoyan_id,
            "maoyan_score": item["sc"],
            "maoyan_actor": item["star"],
            "maoyan_date": item["pubDesc"],
            "maoyan_watch_wish": item["wish"],
            "maoyan_summary": item["shortDec"],
        }
        category = None
        genre = item["cat"]
        region, director = None, None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, **more)
        entries.append(movie)
    return items, entries


def get_maoyan_params(user_agent):
    timestamp = int(datetime.datetime.now().timestamp()*1000)
    index = random.randint(0,9)
    channel = 40011
    version = 1
    f = "&key=A013F70DB97834C0A5492378BD76C53A"
    s = f"method=GET&timeStamp={timestamp}&User-Agent={user_agent}&index={index}&channelId={channel}&sVersion={version}" + f
    signkey = hashlib.md5(s.encode("utf8")).hexdigest()
    params = {
        "channelId": channel,
        "index": index,
        "sVersion": version,
        "signKey": signkey,
        "timeStamp": timestamp,
        "webdriver": False
    }
    return params

def parse_maoyan_detail(page, **kwargs):
    # woff 字体还原 TODO
    font_map = {}
    woff = re.findall(r'url\("//([\w\-./]+\.woff)"\)', page)
    if woff:
        woff = woff[-1]
        logging.info(f"woff font = {woff}")

    soup = BeautifulSoup(page, "html5lib")
    if soup.title:
        logging.info("Process movie = {}".format(soup.title.text))
    elif soup.h1:
        logging.info("Process movie = {}".format(soup.h1.text))

    banner = soup.body.find(class_="banner")
    content = soup.body.find(class_="main-content-container")

    banner_left = banner.find(class_="celeInfo-left")
    img = banner_left.img["src"]

    banner_right = banner.find(class_="celeInfo-right")
    title = strip(banner_right.h1.text)
    title2 = strip(banner_right.find(class_="ename").text)
    info1 = [strip(v.text) for v in banner.find("ul").find_all("li")]  # genre, region/length, release_date
    stats = banner_right.find(class_="movie-stats-container")
    # todo # 空白字体还原
    score, vote, box = None, None, None
    # score = stats.find(class_="score").find("span", class_="index-left")
    # vote = stats.find(class_="score").find("div", class_="index-right")
    # box = stats.find(class_="box")
    # if score:
    #     score = strip(score.text)
    #     score = "".join([font_map.get(c, c) for c in score])
    # if vote:
    #     vote = strip(vote.text)
    #     vote = "".join([font_map.get(c, c) for c in vote])
    # if box:
    #     box = strip(box.text)
    #     box = "".join([font_map.get(c, c) for c in box])

    content1 = content.find(class_="main-content")
    content1 = content1.find(class_="tab-content-container")

    summary = strip(content1.find(class_="dra").text)
    attr = content.find(class_="attribute")
    attrs = [[strip(d.text) for d in div.find_all("div", recursive=False)] for div in
             attr.find_all(class_="attribute-item", recursive=False)]  # 出品发行，技术参数（时长）
    # 票房
    box_info = [strip(div.text) for div in
                content1.find(class_="film-mbox").find_all("div", class_="film-mbox-item", recursive=False)]

    # cgroup = content1.find(class_="celebrity-container").find_all(class_="celebrity-group")
    # awards = content.find("ul", class_="award-list")
    cgroup2 = content1.find(class_="tab-celebrity tab-content").find_all(class_="celebrity-group")  # 人员
    staff = []
    for cg in cgroup2:
        key = cg.find(class_="celebrity-type").text.strip()
        val = []
        for li in cg.find(class_="celebrity-list").find_all("li", recursive=False):
            v = {"name": strip(li.find(class_="name").text)}
            if li.find(class_="role"):
                v["role"] = strip(li.find(class_="role").text)
            val.append(v)
        staff.append([strip(key), val])
    reward2 = content1.find(class_="tab-award tab-content").find_all("li", class_="award-item")  # 奖项
    rewards = [strip(li.text) for li in reward2]

    more = {
        # "maoyan_url": link,
        "maoyan_cover": img,
        "maoyan_titles": [title2],
        "maoyan_score": score,
        "maoyan_vote": vote,
        "maoyan_staff": staff,
        "maoyan_info": info1 + attrs,
        "maoyan_summary": summary,
        "maoyan_boxoffice": [v for v in [box] + box_info if v],
        "maoyao_rewards": rewards,
    }
    category = None
    tag = MovieTag.MAOYAN_DETAIL
    if len(info1) == 3:
        genre, region_length, release_date = info1
        region = region_length.split("/")[0].strip()
        year = extract_year(release_date)
    else:
        year, region, genre = None, None, None
    director = []
    for k, v in staff:
        if "导演" in k:
            director.extend([v0.get("name") for v0 in v])
    movie = Movie(title, category, year, region, director, genre, tag=tag, **more)

    return movie
