import logging
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
        about = "\n".join([v.text for v in dinfo.find(class_="doulist-about").contents])
        about = strip(about, keep=True)
        count = content.find('div', class_='doulist-filter').span  # 片单电影数量
        if count:
            count = int(count.text.strip().strip("()"))
        more = {"author": author, "about": about, "count": count}
        dou_desc.update(more)

    # 分页链接
    paginator = content.find(class_="paginator")
    more_hrefs = [a["href"] for a in paginator.find_all("a", recursive=False)]
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
        next_url = next_url['href']

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
        year = (
            int(str(info[-1].split("\xa0")[0])[:4]) if len(info) == 2 else 0
        )  # todo fix year

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

    paginator = content.find(class_="paginator")
    next_url = paginator.find("span", class_="next").a
    if next_url:
        next_url = next_url['href']

    items = content.find_all("div", class_="doulist-item")
    logging.info(f"items = {len(items)}/{total}")
    entries = []
    for item in items:
        idx = item.find("div", class_="hd").text.strip()
        post = item.find("div", class_="post")
        if post is None:
            logging.warning(f"empty -> {idx}")
            continue

        url = post.a["href"]
        img = post.img["src"]
        title = item.find("div", class_="title").text.strip()
        star = item.find("div", class_="rating").text.strip().split()
        assert 1 <= len(star) <= 2
        if len(star) == 2:
            score, count = star
        else:
            score, count = "", star[-1]
        abstract = item.find("div", class_="abstract")
        if abstract:
            abstract = strip(abstract.text, keep=True)
            abstract = [v.strip() for v in abstract.split("\n")]

        link = url
        year = int("\n".join(abstract).split("年份:")[-1].split("\n")[0].strip())
        score = {"douban-score": score, "douban-vote": count}
        more = {"info": abstract}
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
    summary = strip(summary.span.text, keep=True)
    comments = content.find(id="comments-section")
    if comments:
        comments = comments.h2
    else:
        comments = content.find("h2", id="comment_short_tab")
    comments = strip(comments.a.text)
    reviews = content.find(id="reviews-wrapper")
    if not reviews:
        reviews = content.find(id="review_section")
    if not reviews:
        reviews = content.find("h2", class_="clearfix")
        if not reviews:
            reviews = content.find(class_="reviews mod movie-content").h2
        reviews = reviews.find("span", class_="pl")
    else:
        reviews = reviews.h2
    reviews = strip(reviews.a.text)
    discussion = content.find(class_="section-discussion")
    if discussion:
        if discussion.find("p", class_="pl"):
            discussion = strip(discussion.find("p", class_="pl").a.text)
        else:
            discussion = strip(discussion.find("p", class_="discussion_link").a.text)
    elif content.find("h2", class_="discussion_link"):
        discussion = strip(content.find("h2", class_="discussion_link").text)
    else:
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
    else:
        watch = content.find(id="collector").find_all("p", class_="pl")
        watch = [strip(v.text) for v in watch]
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
