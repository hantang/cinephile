import logging
import re

from bs4 import BeautifulSoup

from cinephile.utils.movies import Movie, DoubanMovie, MovieTag
from cinephile.utils.texts import strip


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
        # return None

    grid_view = content.find("ol", class_="grid_view")
    if not grid_view:
        logging.warning("grid_view is null")
        # return None

    paginator = content.find(class_="paginator")
    next_url = paginator.find("span", class_="next").a
    if next_url:
        next_url = next_url["href"]

    items = grid_view.find_all("li")
    logging.info(f"items = {len(items)}/{total}")

    entries = []
    tag = MovieTag.DOUBAN_TOP250
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
        star = bd.find(class_="star")
        star_score = star.select_one(".rating_num").text
        star_count = star.find_all("span")[-1].text
        quote = bd.find(class_="quote")
        quote = quote.text.strip() if quote else ""
        extra = {
            "douban-url": link,
            "douban-cover": img,
            "douban-score": star_score,
            "douban-vote": star_count,
            "douban-titles": titles,
            "douban-info": info,
            "douban-quote": quote,
        }
        info_part1 = dict([v.split(":") for v in info[0].split("\xa0") if v and ':' in v])
        director = info_part1.get("导演")
        info_part2 = [v.strip() for v in info[1].split("\xa0/\xa0")]
        assert len(info_part2) == 3
        year_raw, region, genre = info_part2
        years = re.findall(r"\d{4}", year_raw)
        year = int(years[0]) if years else 0
        category = None
        douban_id = link.strip("/").split("subject/")[-1] if link else None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, douban_id=douban_id, **extra)
        entries.append(movie)

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
    tag = MovieTag.DOUBAN_HOT
    for item in items:
        title = item["title"]
        link = item["uri"]
        img = item["pic"]["normal"]
        mtype = item.get("type_name", item.get("type"))
        rank = item.get("rank_value", item.get("rank"))
        if "year" in item:  # 实时
            year = item["year"][:4]
        else:  # 实时/热门
            year = item["card_subtitle"].split("/")[0].strip()[:4]
        info2 = [item["info"]] if "info" in item else []  # 实时
        comments = item.get("comments", [])
        comments = [(v["comment"], v["rating"]["star_count"]) for v in comments]
        extra = {
            "douban-url": link,
            "douban-cover": img,
            "douban-score": item["rating"]["value"],
            "douban-vote": item["rating"]["count"],
            # "douban-titles": titles,
            "douban-info": [item["card_subtitle"]] + info2,
            "douban-reward": [v["title"] for v in item["honor_infos"]],
            "douban-comment": [f"{v1} (star={v2})" for v1, v2 in comments],  # 实时
            "douban-tag": [v["name"] for v in item.get("tags", [])],  # 热门
            "douban-summary": item.get("description"),  # 热门
        }

        category = None  # todo
        douban_id = item["id"]
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, douban_id=douban_id, **extra)
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
    tag = MovieTag.DOUBAN_LIST
    for item in items:
        idx = item.find("div", class_="hd").text.strip()
        bd = item.find("div", class_="bd")
        ft = item.find("div", class_="ft")
        post = bd.find("div", class_="post")
        if post is None:
            logging.warning(f"empty -> {idx}")
            movie = Movie("", None, None, None, None, None, tag=tag, rank=idx, douban_id=None)
            entries.append(movie)
            continue

        link = post.a["href"]
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
        extra = {
            "douban-url": link,
            "douban-cover": img,
            "douban-score": score,
            "douban-vote": count,
            # "douban-titles": titles,
            "douban-info": abstract,
            "douban-comment": [comment, actions]
        }

        category = None  # todo
        info_dict = dict([v.split(":") for v in abstract])
        director = info_dict.get("导演")
        genre = info_dict.get("类型")
        region = info_dict.get("制片国家/地区")
        year = info_dict.get("年份")
        year = int(year.strip()) if year and year.strip().isdigit() else 0
        douban_id = link.strip("/").split("subject/")[-1] if link else None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=idx, douban_id=douban_id, **extra)
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
    logging.info("Process movie = {}".format(strip(soup.title.text)))

    wrapper = soup.body.find(id="wrapper")
    content = wrapper.find(id="content")
    if not content:
        logging.warning(f"Error douban-movie-id = {movie_id}")
        # return None

    rank = content.find(class_="top250-no")
    rank = strip(rank.text) if rank else ""
    h1 = content.h1 if content.h1 else wrapper.h1
    title, year = [strip(v.text) for v in h1.select("span")]

    article = content.find(class_="article")
    if ("在看" in strip(article.find(id="interest_sect_level").text)) or \
            article.find("div", class_="episode_list"):
        category = "tv"
    else:
        category = "movie"

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
            count = strip(t2[1].text)
            weight_cnt = 5  # 五星评级
            weight = [[t2[i]["title"], strip(t2[i + 1].text)] for i in range(2, weight_cnt * 2, 2)]
        betterthan = right.find(class_="rating_betterthan")
        if betterthan:
            betterthan = strip(betterthan.text)
    else:
        # 部分词条没有评分、影评
        # https://movie.douban.com/subject/1293408/  小活佛 Little Buddha (1993)
        score, count, weight, betterthan = "", "", [], ""
    left = article.find(class_="subject clearfix")
    pic = left.find(id="mainpic")
    cover = pic.img["alt"]
    url = pic.a["href"].split("/photos?")[0]
    if not movie_id:
        movie_id = url.strip("/").split("/")[-1]
    # 分享按钮
    # rec = content.find(class_="gtleft").find(class_="rec")
    info = left.find(id="info")
    info_result = _parse_douban_info(info)

    # 剧情简介
    summary = content.find(id="link-report-intra")
    if not summary:
        summary = content.find(class_="related-info")
    if not summary:
        summary = content.find(id="link-report")
    if summary.span:
        summary = strip(summary.span.text, keep=True)
    else:
        summary = None
    # 视频和图片
    resources = content.find(id="related-pic").find("span", class_="pl")
    if resources:
        resources = strip(resources.text)
    # 获奖 
    rewards = [strip(v.text) for v in content.find_all("ul", class_="award")]
    # 短评
    comments = content.find(id="comments-section")
    if comments:
        comments = comments.h2
    else:
        comments = content.find("h2", id="comment_short_tab")
    if comments and comments.a:
        comments = strip(comments.a.text)
    else:
        comments = None
    # 影评
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
    # 讨论区
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
    discussion = "/".join([v for v in [discussion, discussion2] if v])

    # 问题
    question = content.find(id="askmatrix")
    if question:
        question = strip(question.h2.a.text)
    # 想看/看过/在看
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

    info_dict = dict(info_result)
    used_keys = ["导演", "编剧", "主演", "类型", "制片国家/地区", "语言", "上映日期", "片长", "又名", "IMDb",
                 "官方网站"]
    director = info_dict["导演"]
    writers = info_dict.get("编剧")
    actors = info_dict.get("主演")
    genre = info_dict.get("类型")
    region = info_dict.get("制片国家/地区")
    languages = info_dict.get("语言")
    release_date = info_dict.get("上映日期")
    length = info_dict.get("片长")
    title_alias = info_dict.get("又名")
    imdb_id = info_dict.get("IMDb")
    websites = info_dict.get("官方网站")
    extra = {key: val for key, val in info_dict.items() if key not in used_keys}

    year_part = re.findall(r"\d{4}", year)
    year = int(year_part[0]) if year_part else 0
    if resources:
        resources = dict(re.findall(r"([^\d\s]+)(\d+)", resources))
    if discussion:
        discussion_result = re.findall(r"全部\s*\d+\s*条", discussion)
        if discussion_result:
            discussion = discussion_result[0]

    douban_url = url
    douban_cover = cover
    douban_rank = rank
    douban_id = movie_id
    score_count = count
    score_weights = weight
    watching = watch
    douban = DoubanMovie(title,
                         category,
                         year,
                         region,
                         director,
                         genre,
                         douban_url,
                         douban_cover,
                         douban_rank,
                         douban_id,
                         writers,
                         actors,
                         languages,
                         release_date,
                         websites,
                         length,
                         title_alias,
                         imdb_id,
                         score,
                         score_count,
                         score_weights,
                         summary,
                         resources,
                         rewards,
                         comments,
                         reviews,
                         discussion,
                         question,
                         watching,
                         **extra)
    tag = MovieTag.DOUBAN_DETAIL
    movie = Movie(title, category, year, region, director, genre, tag=tag, douban=douban)
    return movie
