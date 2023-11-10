import json
import logging

import pandas as pd
from bs4 import BeautifulSoup
from cinephile.utils.texts import strip
from cinephile.utils.movies import Movie


def extract_page_info(page, desc=None):
    # 获取Top250或者豆列信息和对应下载页面列表。
    logging.info("extract paginator ...")
    soup = BeautifulSoup(page, "html5lib")
    logging.info("Title = {}".format(soup.title.text.strip()))
    wrapper = soup.body.find(id="wrapper")
    content = wrapper.find(id="content")
    if not content:
        logging.warning(f"Error {desc}")
        return None, None

    douname = strip(content.h1.text)
    dou_desc = {"name": douname}
    dinfo = content.find(id="doulist-info")
    if dinfo:
        author = strip(dinfo.find(class_="meta").text)
        about = dinfo.find(class_="doulist-about")
        if about:
            about = "\n".join([v.text for v in about.contents])
            about = strip(about, keep=True)
        else:
            about = ""
        count = content.find("div", class_="doulist-filter").span  # 片单电影数量
        if count:
            count = int(count.text.strip().strip("()"))
        more = {"author": author, "about": about, "count": count}
        dou_desc.update(more)

    # 分页链接
    paginator = content.find(class_="paginator")
    more_hrefs = [a["href"] for a in paginator.find_all("a", recursive=False)] if paginator else []
    logging.info("FIN extract paginator ...")
    logging.info(f"more_hrefs = {len(more_hrefs)}, dou_desc = {dou_desc}")
    return more_hrefs, dou_desc


def parse_page_top250(page, **kwargs):
    """解析豆瓣top250页面
    https://movie.douban.com/top250
    ~~http://www.douban.com/movie/top250~~
    """
    logging.debug("parse page: douban top250")
    total = kwargs.get("total", 25)
    soup = BeautifulSoup(page, "html5lib")
    logging.info("Title: {}".format(soup.title.text.strip()))

    wrapper = soup.body.find(id="wrapper")
    content = wrapper.find(id="content")
    if not content:
        logging.warning(f"Error Top250")
        return None

    grid_view = content.find("ol", class_="grid_view")
    if not grid_view:
        logging.warning("grid_view is null")
        return None

    paginator = content.find(class_="paginator")
    next_url = paginator.find("span", class_="next").a
    if next_url:
        next_url = next_url["href"]

    items = grid_view.find_all("li")
    logging.info(f"items = {len(items)}/{total}")

    entries = []
    # info_keys = ["director", "actor", "year", "region", "genre"]
    for item in items:
        tpic = item.find(class_="pic")
        rank = tpic.em.text.strip()
        title = tpic.a.img["alt"]
        link = tpic.a["href"]
        img = tpic.a.img["src"]

        hd = item.find(class_="hd")
        titles = [strip(v.text, slash=True) for v in hd.a.find_all("span")]

        bd = item.find(class_="bd")
        info = [v.text.strip() for v in bd.p.contents if not v.name]
        year = (int(str(info[-1].split("\xa0")[0])[:4]) if len(info) == 2 else 0)

        star = bd.find(class_="star")
        star_score = star.select_one(".rating_num").text
        star_count = star.find_all("span")[-1].text
        quote = bd.find(class_="quote")
        quote = quote.text.strip() if quote else ""
        score = {
            "douban-score": star_score,
            "douban-vote": star_count,
        }
        more = {
            "title-more": titles,
            "douban-info": info,
            "douban-quote": quote,
        }
        entry = Movie(title, link, img, year, rank, mtype=None, score=score, **more)
        entries.append(entry)
    logging.info(f"output entries = {len(entries)} / {total}")
    return entries, next_url


def parse_page_hot(page, **kwargs):
    # 热门或实时
    if "desc" in kwargs:
        logging.info("parse page: douban hot - {}".format(kwargs["desc"]))
    else:
        logging.info("parse page: douban hot")
    logging.info(f"page keys = {page.keys()}")
    items = page["subject_collection_items"]
    total = page["total"]
    logging.info(f"items = {len(items)}/{total}")
    entries = []
    for item in items:
        title = item["title"]
        link = item["uri"]
        img = item["pic"]["normal"]
        mtype = item.get("type_name", item.get("type"))  # 实时/热门
        rank = item.get("rank_value", item.get("rank"))  # 实时/热门
        if "year" in item:  # 实时
            year = item["year"][:4]
        else:  # 实时/热门
            year = item["card_subtitle"].split("/")[0].strip()[:4]
        info2 = [item["info"]] if "info" in item else []  # 实时
        comments = item.get("comments", [])
        comments = [(v["comment"], v["rating"]["star_count"]) for v in comments]
        score = {
            "douban-score": item["rating"]["value"],
            "douban-vote": item["rating"]["count"],
        }
        more = {
            "douban-id": item["id"],
            "douban-info": [item["card_subtitle"]] + info2,
            "reward": [v["title"] for v in item["honor_infos"]],
            "comment": [f"{v1} (star={v2})" for v1, v2 in comments],  # 实时
            "tag": [v["name"] for v in item.get("tags", [])],  # 热门
            "summary": item.get("description"),  # 热门
        }
        movie = Movie(title, link, img, year, rank, mtype=mtype, score=score, **more)
        entries.append(movie)
    logging.info(f"output entries = {len(entries)} / {total}")
    return items, entries


def parse_page_list(page, **kwargs):
    """豆瓣豆列（片单）
    eg: https://www.douban.com/doulist/240962/
    "https://www.douban.com/doulist/{doulist-id}/?start={page}&sort=seq&playable=0&sub_type=",
    # url = url_pattern + f"?start={num}&sort=time&playable=0&sub_type="
    # url = url_pattern + f"?start={num}&sort=seq&playable=0&sub_type="
    """
    logging.debug("parse page: douban movie list")
    doulist = kwargs.get("movie_list_id")
    total = kwargs.get("total", 25)
    soup = BeautifulSoup(page, "html5lib")
    logging.info("Title = {}".format(soup.title.text.strip()))
    wrapper = soup.body.find(id="wrapper")
    content = wrapper.find(id="content")
    if not content:
        logging.warning(f"Error movie list id = {doulist}")
        return None

    next_url = "#"
    paginator = content.find(class_="paginator")
    if paginator and paginator.find("span", class_="next").a:
        next_url = paginator.find("span", class_="next").a["href"]

    items = content.find_all("div", class_="doulist-item")
    logging.info(f"items = {len(items)}/{total}")
    entries = []
    for item in items:
        idx = item.find("div", class_="hd").text.strip()
        bd = item.find("div", class_="bd")
        ft = item.find("div", class_="ft")
        post = bd.find("div", class_="post")
        if post is None:
            logging.warning(f"empty -> {idx}")
            movie = Movie("", None, None, 0, rank=idx, mtype=None, score=None)
            entries.append(movie)
            continue

        url = post.a["href"]
        img = post.img["src"]

        title = bd.find("div", class_="title").text.strip()
        star = bd.find("div", class_="rating")
        score, count = "", ""
        if star:
            star = star.text.strip().split()
            # assert 1 <= len(star) <= 2
            if len(star) == 2:
                score, count = star[0], star[1]
            elif len(star) == 1:
                count = star[0]
        abstract = bd.find("div", class_="abstract")
        if abstract:
            abstract = strip(abstract.text, keep=True)
            abstract = [v.strip() for v in abstract.split("\n")]

        comment, actions = None, None
        if ft:
            comment = ft.find(class_="comment-item")
            if comment:
                comment = strip(comment.text)
            actions = ft.find(class_="actions")
            if actions:
                actions = strip(actions.text)

        link = url
        year = "\n".join(abstract).split("年份:")[-1].split("\n")[0].strip()
        year = int(year) if year.isdigit() else 0
        score = {"douban-score": score, "douban-vote": count}
        more = {"info": abstract, "comment": [comment, actions]}
        movie = Movie(title, link, img, year, rank=idx, mtype=None, score=score, **more)
        entries.append(movie)
    logging.info(f"entries = {len(entries)}/ {total}")
    return entries, next_url


def parse_page_detail(page, **kwargs):
    """豆瓣电影详情页
    https://movie.douban.com/subject/1292722/
    """

    def _parse_douban_info(douban_info):
        groups = []
        temp = []
        for child in douban_info.children:
            if child.name is None and child.text.strip() == "":
                continue
            if child.name == "br" and temp:
                groups.append(temp)
                temp = []
            else:
                temp.append(child)
        if temp:
            groups.append(temp)
        result = []
        for i, group in enumerate(groups):
            spans = group[0].find_all("span")
            if spans:
                assert len(group) == 1
                if len(spans) > 1:
                    val = [strip(v.text, slash=True) for v in spans]
                else:
                    val = [strip(v.text) for v in group[0].children]
                    val = [v for v in val if v != ":"]
                    val = [val[0], " ".join(val[1:]).strip()]
            else:
                val = [strip(v.text) for v in group]
                val = [val[0].rstrip(":"), " ".join(val[1:]).strip()]
            assert len(val) == 2
            result.append(val)
        return result

    logging.debug("parse page: douban page detail")
    movie_id = kwargs.get("movie_id")

    soup = BeautifulSoup(page, "html5lib")
    logging.info(soup.title.text.strip())
    wrapper = soup.body.find(id="wrapper")
    content = wrapper.find(id="content")
    if not content:
        logging.warning(f"Error douban-movie-id = {movie_id}")
        return None

    rank = content.find(class_="top250-no")
    rank = strip(rank.text) if rank else ""
    h1 = content.h1 if content.h1 else wrapper.h1
    title, year = [strip(v.text) for v in h1.select("span")]

    article = content.find(class_="article")
    right = article.find(id="interest_sectl")
    if right:
        if right.find(class_="rating_sum"):
            score = strip(right.find(class_="ll rating_num").text)
            count = strip(right.find(class_="rating_sum").text)
            weight = right.find(class_="ratings-on-weight")
            weight = [strip(v.text) for v in weight.find_all("div", class_="item")]
        else:
            star_path = right.find(class_="rating_wrap clearbox")
            t = list(star_path.children)
            t2 = [v for v in t if v.name in ["p", "span"] or "%" in v.text]
            score = t2[0].find(class_="ll rating_num").text
            count = t2[1].text.strip()
            weight_cnt = 5  # 五星评级
            weight = [[t2[i]["title"], t2[i + 1].text.strip()] for i in range(2, weight_cnt * 2, 2)]
    else:
        # 部分词条没有评分、影评
        # https://movie.douban.com/subject/1293408/  小活佛 Little Buddha (1993)
        score, count, weight = "", "", []
    left = article.find(class_="subject clearfix")
    pic = left.find(id="mainpic")
    alt = pic.img["alt"]

    # 分享按钮
    rec = content.find(class_="gtleft").find(class_="rec")
    if rec:
        mtype = rec.a.get("data-type")
        if not mtype:
            mtype = rec.a["data-title"].split("《")[0]
        link = rec.a["data-url"]
        img = rec.a["data-pic"]
    else:
        mtype = None
        img = pic.img["src"]
        link = pic.a["href"].split("photo")[0]
    if not movie_id:
        movie_id = link.strip("/").split("/")[-1]

    info = left.find(id="info")
    info_result = _parse_douban_info(info)

    rewards = [strip(v.text) for v in content.find_all("ul", class_="award")]
    summary = content.find(id="link-report-intra")
    if not summary:
        summary = content.find(class_="related-info")
    if not summary:
        summary = content.find(id="link-report")
    if summary.span:
        summary = strip(summary.span.text, keep=True)
    else:
        summary = None
    comments = content.find(id="comments-section")
    if comments:
        comments = comments.h2
    else:
        comments = content.find("h2", id="comment_short_tab")
    if comments and comments.a:
        comments = strip(comments.a.text)
    else:
        comments = None
    reviews = content.find(id="reviews-wrapper")
    if not reviews:
        reviews = content.find(id="review_section")
    if not reviews:
        reviews = content.find("h2", class_="clearfix")
        if not reviews and content.find(class_="reviews mod movie-content"):
            reviews = content.find(class_="reviews mod movie-content").h2
        if reviews:
            reviews = reviews.find("span", class_="pl")
    else:
        reviews = reviews.h2
    if reviews and reviews.a:
        reviews = strip(reviews.a.text)
    else:
        reviews = None
    discussion = content.find(class_="section-discussion")
    if discussion:
        if discussion.find("p", class_="pl"):
            discussion = strip(discussion.find("p", class_="pl").a.text)
        else:
            discussion = strip(discussion.find("p", class_="discussion_link").a.text)
    elif content.find("h2", class_="discussion_link"):
        discussion = strip(content.find("h2", class_="discussion_link").text)
    elif content.find(id="db-discussion-section"):
        discussion = strip(
            content.find(id="db-discussion-section").find("p", class_="pl").text
        )
    discussion2 = content.find(class_="mv-discussion-list discussion-list")
    if discussion2:
        discussion2 = strip(discussion2.table.next_sibling.next_sibling.text)
    question = content.find(id="askmatrix")
    if question:
        question = strip(question.h2.a.text)
    if content.find(id="subject-others-interests"):
        watch = content.find(id="subject-others-interests").find(
            "div", class_="subject-others-interests-ft"
        )
        watch = [strip(v.text) for v in watch.find_all("a")]
    elif content.find(id="collector"):
        watch = content.find(id="collector").find_all("p", class_="pl")
        watch = [strip(v.text) for v in watch]
    else:
        watch = None
    year = int(year.strip("()"))
    score = {
        "douban-score": score,
        "douban-vote": count,
        "douban-weight": weight,
    }
    more = {
        "douban-id": movie_id,
        "title-more": alt,
        "info": info_result,
        "rewards": rewards,
        "summary": summary,
        "comments": comments,
        "reviews": reviews,
        "discussion": discussion,
        "discussion-list": discussion2,
        "question": question,
        "watch": watch,
    }
    movie = Movie(title, link, img, year, rank, mtype=mtype, score=score, **more)
    return movie


def parse_annual_data(page, **kwargs):
    """豆瓣年度榜单，转化成csv"""

    def _get_id_link(url):
        url = url.strip()
        if not url:
            return " "
        v = url.strip("/").split("/")[-1]
        return "[{}]({})".format(v, url)

    def _get_title(x):
        title = " / ".join([v.strip() for v in [x["title"], x["orig_title"]] if v.strip() != ""])
        return " " if title == "" else title

    keys = [
        "description",
        "info",
        "orig_title",
        "rating",
        "title",
        "type",
        "url",
        "cover",
        # "done_count",
        # "rating_count",
        # "rating_stats",
        # "short_info",
    ]

    cols_out = ["Group 分类", "Rank 排名", "Title 电影", "ID 豆瓣", "Score 打分", "Staff 人员", "Region 地区", ]
    cols_raw = ["group", "rank", "title2", "id", "rating", "info", "description"]
    data = page
    data2 = []
    for entry in data["res"]["widgets"]:
        if "show_kind" in entry and "widgets" in entry["payload"]:
            for entry2 in entry["payload"]["widgets"]:
                if "show_kind" not in entry2:
                    data2.append(entry2)
        else:
            data2.append(entry)

    data3 = []
    for entry in data2:
        payload = entry["payload"]
        entry2 = {k: entry.get(k) for k in ["kind_cn", "kind_str", "subjects"]}
        if not entry2["subjects"]:
            if "items" not in payload:
                continue
            items = payload["items"]
            entry2["subjects"] = json.loads(items) if isinstance(items, str) else items
        if not entry2["subjects"]: continue

        t = payload["title"].strip()
        t1 = payload.get("subtitle", "").strip()
        # 仅保留了电影类，去除剧集、综艺和其他
        if not ("电影" in t or t.endswith("片") or t.endswith("佳作")):
            logging.info(f"ignore: {t}")
            continue
        entry2["group"] = "-".join([v for v in [t1, t] if v])
        data3.append(entry2)

    data4 = []
    for e in data3:
        for i, v in enumerate(e["subjects"]):
            e2 = {k: e[k] for k in ["group"]}
            e2["rank"] = i + 1
            if "cover" in v:
                e2.update({k: v[k] for k in keys})
            else:
                e2["desc"] = v["subtitle"]
                if "subject" in v:
                    e2.update({k: v["subject"].get(k) for k in keys})
            data4.append(e2)
        data4.append({})  # 不同榜单分组加入空白行
    if not data4[-1]:
        data4 = data4[:-1]
    if len(data4) == 0:
        return None

    df = pd.DataFrame(data4[:-1])
    df = df.fillna(" ").astype(str)
    df["id"] = df["url"].apply(_get_id_link)
    df["title2"] = df.apply(lambda x: _get_title(x), axis=1)
    df["rank"] = df["rank"].apply(lambda x: x.split(".")[0])
    df["rating"] = df["rating"].apply(lambda x: "{:.1f}".format(float(x)) if x != " " else " ")
    logging.info(df['group'].value_counts())

    df2 = df[cols_raw].copy()
    df2.columns = cols_out
    return df2
