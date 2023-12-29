import json
import logging

import pandas as pd

from cinephile.utils.movies import Movie, MovieTag


def _is_movie_list(title):
    # 仅保留了电影类，去除剧集、综艺和其他
    return "电影" in title or title.endswith("片") or title.endswith("佳作")


def parse_annual_data(page, **kwargs):
    """豆瓣年度榜单"""

    def _get_id_link(url):
        url = url.strip()
        if not url:
            return " "
        v = url.strip("/").split("/")[-1]
        return "[{}]({})".format(v, url)

    annual = kwargs.get("year", 0)
    if annual <= 2022:
        items_list, entries_list = parse_annual_data1(page, **kwargs)
    else:
        items_list, entries_list = parse_annual_data2(page, **kwargs)

    data = []
    groups = []
    for items, entries in zip(items_list, entries_list):
        if "payload" in items:
            payload = items["payload"]
            group = "".join([v.strip() for v in [payload.get("subtitle", ""), payload["title"]]])
            group = group.replace(" ", "").strip()
            if not group.startswith("豆瓣"):
                group = "豆瓣" + group
        else:
            group = items["subject_collection"]["title"].strip()
        groups.append(group)
    #     for movie in entries:
    #         entry = {
    #             "group": group,
    #             "rank": movie.rank,
    #             "title": movie.title,
    #             "id": _get_id_link(movie.link),
    #             "score": movie.score.get("douban-score", 0),
    #             "staff": movie.more.get("staff"),
    #             "region": movie.more.get("region"),
    #         }
    #         data.append(entry)
    #     data.append({})
    # if not data[-1]:
    #     data = data[:-1]
    # if len(data) == 0:
    #     return items_list, entries_list, None, None
    #
    # df = pd.DataFrame(data)
    # df = df.fillna(" ").astype(str)
    # df["rank"] = df["rank"].apply(lambda x: x.split(".0")[0])
    # df["score"] = df["score"].apply(lambda x: "{:.1f}".format(float(x)) if x != " " else " ")
    # logging.info(df["group"].value_counts())
    # cols_out = ["Group 分类", "Rank 排名", "Title 电影", "ID 豆瓣", "Score 打分", "Staff 人员", "Region 地区", ]
    # df.columns = cols_out
    return items_list, entries_list, groups # , df


def parse_annual_data0(page, **kwargs):
    """豆瓣年度榜单 2014"""
    pass  # todo


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
        payload = entry["payload"]
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
            score, count = item["rating"], item["rating_count"]
            extra = {
                "douban-url": link,
                "douban-cover": img,
                "douban-score": score,
                "douban-vote": count,
                "douban-staff": item["info"],
                "douban-title-orig": item["orig_title"],
            }
            category = "movie"
            region = item["description"]
            year = int(item.get("year", 0))
            director = item["info"].split("/")[0].strip()
            genre = None
            rank = idx
            douban_id = link.strip("/").split("subject/")[-1] if link else None
            movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, douban_id=douban_id, **extra)
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
            count = item["rating"]["rating_count"]
            parts = [p.strip() for p in item["card_subtitle"].split("/")]
            year, region, genre, staff = (
                parts[0],
                parts[1],
                parts[2],
                " / ".join(parts[3:]),
            )
            year = int(year)
            extra = {
                "douban-url": link,
                "douban-cover": img,
                "douban-score": score,
                "douban-vote": count,
                "douban-region": region,
                "douban-staff": staff,
            }
            douban_id = link.strip("/").split("subject/")[-1] if link else None
            category = "movie"
            director = staff.split("/")[0].strip()
            rank = idx
            movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, douban_id=douban_id, **extra)
            entries.append(movie)
        entries_list.append(entries)
    return items_list, entries_list
