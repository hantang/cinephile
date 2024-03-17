import json
import logging

from bs4 import BeautifulSoup

from cinephile.utils.movies import Movie, MovieTag
from cinephile.utils.texts import strip


def _is_movie_list(title):
    # 仅保留了电影类，去除剧集、综艺和其他
    return "电影" in title or title.endswith("片") or title.endswith("佳作")


def parse_annual_data(page, **kwargs):
    """豆瓣年度榜单"""

    # def _get_id_link(url):
    #     url = url.strip()
    #     if not url:
    #         return " "
    #     v = url.strip("/").split("/")[-1]
    #     return "[{}]({})".format(v, url)

    annual = kwargs.get("year", 0)
    if annual == 2014:
        items_list, entries_list = parse_annual_data0(page, **kwargs)
    elif annual <= 2022:
        items_list, entries_list = parse_annual_data1(page, **kwargs)
    else:
        items_list, entries_list = parse_annual_data2(page, **kwargs)

    groups = []
    for items, entries in zip(items_list, entries_list):
        if "payload" in items:
            payload = items["payload"]
            group = "".join([v.strip() for v in [payload.get("subtitle", ""), payload["title"]]])
            group = group.replace(" ", "").strip()
            if not group.startswith("豆瓣"):
                group = "豆瓣" + group
        elif "subject_collection" in items:
            group = items["subject_collection"]["title"].strip()
        else:
            group = " | ".join(strip(items[k]) for k in ["douban_group", "douban_tips", "douban_comment"])
        groups.append(group)
    return items_list, entries_list, groups


def parse_annual_data0(page, **kwargs):
    """豆瓣年度榜单 2014"""
    soup = BeautifulSoup(page, "html5lib")
    logging.info("Process movie = {}".format(strip(soup.title.text)))

    div_main = soup.body.find("div", class_="main")

    sections = div_main.find_all("div", class_="section", recursive=False)
    items_list = []
    entries_list = []
    tag = MovieTag.DOUBAN_ANNUAL
    for i, items in enumerate(sections):
        if "typeA" not in items["class"] or not items.h1:
            if items.h1:
                logging.info(f"Skip = {i}, {items.h1.text.strip()}")
            continue

        wp = items.find("div", "wp")
        more = items.find("div", "more")
        group = wp.h1.text.strip()
        if not _is_movie_list(group):
            logging.info(f"Ignore annual list = {group}")
            continue
        desc = wp.find("div", class_="desc")
        # desc.find("span", class_="collections").text.strip()
        # desc.find("span", class_="rank").text.strip()
        tips = desc.find("p", class_="tips").text.strip()
        comment = more.find("div", class_="fleft").text.strip()
        alist = more.find("div", class_="fright").find_all("a", recursive=False)
        assert len(alist) in [5, 10]
        entries = []
        for item in alist:
            link = item["href"]
            img = item.img["src"]
            rank = item.find("span", class_="num").text.strip()
            subject_info = item.find(class_="subject_info")
            plist = [p.text.strip() for p in subject_info.find_all("p")]
            s = subject_info.strong
            score = None
            if s.span:
                score = s.span.text.strip()
                s.span.decompose()
            title = s.text.strip()
            extra = {
                "douban_url": link,
                "douban_cover": img,
                "douban_score": score,
                "douban_info": plist,
            }
            category = "movie"
            region = None
            year = 0
            info_dict = dict([p.split("：") for p in plist])
            director = info_dict.get("导演")
            genre = info_dict.get("类型")
            douban_id = link.strip("/").split("subject/")[-1] if link else None
            movie = Movie(title, category, year, region, director, genre,
                          tag=tag, rank=rank, douban_id=douban_id, **extra)
            entries.append(movie)
        items_new = {
            "douban_tips": tips,
            "douban_comment": comment,
            "douban_group": group,
        }
        items_list.append(items_new)
        entries_list.append(entries)
    return items_list, entries_list


def parse_annual_data1(page, **kwargs):
    """豆瓣年度榜单 2015-2022"""
    widgets = []
    data = page["res"]
    for entry in data["widgets"]:
        if "show_kind" in entry and "widgets" in entry["payload"]:
            for entry2 in entry["payload"]["widgets"]:
                if "show_kind" not in entry2:
                    widgets.append(entry2)
        else:
            widgets.append(entry)

    items_list = []
    for widget in widgets[:]:
        payload = widget["payload"]
        if widget.get("subjects") or "items" in payload:
            t = payload.get("title", "").strip()
            if _is_movie_list(t):
                items_list.append(widget)
            else:
                print(f"ignore = {t}")

    entries_list = []
    tag = MovieTag.DOUBAN_ANNUAL
    for widget in items_list[:]:
        payload = widget["payload"]
        items = widget.get("subjects", payload.get("items"))
        assert items is not None
        if isinstance(items, str):
            items = json.loads(items)

        entries = []
        for idx, item in enumerate(items):
            idx += 1
            link = item["url"]
            img = item["cover"]
            title = item["title"]
            score = item["rating"]
            vote = item["rating_count"]
            weights = item["rating_stats"]
            extra = {
                "douban_url": link,
                "douban_cover": img,
                "douban_score": score,
                "douban_vote": vote,
                "douban_weights": weights,
                "douban_staff": item["info"],
                "douban_title_orig": item["orig_title"],
            }
            category = "movie"
            region = item["description"]
            year = int(item.get("year", 0))
            director = item["info"].split("/")[0].strip()
            genre = None
            rank = idx
            douban_id = link.strip("/").split("subject/")[-1] if link else None
            movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, douban_id=douban_id,
                          **extra)
            entries.append(movie)
        entries_list.append(entries)
    return items_list, entries_list


def parse_annual_data2(page, **kwargs):
    """豆瓣年度榜单 2023"""
    data = page
    items_list = []
    for entry in data["widgets"]:
        sources = entry["source_data"]
        t = entry["title"].strip()
        if not (t and sources):
            continue
        if not isinstance(sources, list):
            sources = [sources]
        for source in sources:
            if "subject_collection" not in source:
                continue
            t = source["subject_collection"]["title"].strip()
            if not _is_movie_list(t):
                print(f"ignore: {t}")
                continue
            items_list.append(source)

    entries_list = []
    tag = MovieTag.DOUBAN_ANNUAL
    for widget in items_list:
        items = widget["subject_collection_items"]
        entries = []
        for idx, item in enumerate(items):
            idx += 1
            link = item["url"]
            img = item["cover_url"]
            title = item["title"]
            score = item["rating"]["value"]
            vote = item["rating"]["rating_count"]
            parts = [p.strip() for p in item["card_subtitle"].split("/")]
            year, region, genre, staff = (
                parts[0],
                parts[1],
                parts[2],
                " / ".join(parts[3:]),
            )
            year = int(year)
            extra = {
                "douban_url": link,
                "douban_cover": img,
                "douban_score": score,
                "douban_vote": vote,
                "douban_region": region,
                "douban_staff": staff,
            }
            douban_id = link.strip("/").split("subject/")[-1] if link else None
            category = "movie"
            director = staff.split("/")[0].strip()
            rank = idx
            movie = Movie(title, category, year, region, director, genre,
                          tag=tag, rank=rank, douban_id=douban_id, **extra)
            entries.append(movie)
        entries_list.append(entries)
    return items_list, entries_list
