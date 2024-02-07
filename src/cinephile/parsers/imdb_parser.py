import json
import logging
import re

from bs4 import BeautifulSoup

from cinephile.utils.movies import Movie, ImdbMovie, MovieTag
from cinephile.utils.texts import strip, extract_year


def extract_imdb_page_info(page, desc=None):
    # 获取IMDB豆列信息和对应下载页面列表。
    logging.info("extract paginator: {} ...".format(desc if desc else ""))
    soup = BeautifulSoup(page, "html5lib")
    logging.info("Title = {}".format(strip(soup.title.text)))

    div_main = soup.body.find(id="main")
    name = div_main.h1.text.strip()
    author = strip(div_main.find(id="list-overview-summary").text)
    list_desc = {"name": name, "author": author, }
    # 总数
    # pagi = div_main.find(class_="list-pagination")
    # pagi.find(class_="next-page")["href"]
    # total = int(pagi.find(class_="pagination-range").text.strip().split("of")[-1])
    total_num = div_main.find(class_="desc lister-total-num-results").text.strip()
    total_num = int(total_num.split()[0].replace(",", ""))

    return total_num, list_desc


def parse_imdb_page_top_v4(page, **kwargs):
    total = kwargs["total"]
    base_url = kwargs["base_url"].rstrip("/")

    tag1 = """<script id="__NEXT_DATA__" type="application/json">"""
    tag2 = "</script>"
    pattern = rf"{tag1}.+?{tag2}"

    out = re.findall(pattern, page)
    if len(out) != 1:
        logging.error(f"parse error of pattern = {pattern}")
        return None

    json_data = json.loads(out[0].split(tag1)[-1].split(tag2)[0])
    items = json_data["props"]["pageProps"]["pageData"]["chartTitles"]["edges"]

    if len(items) != total:
        logging.warning(f"error items count = {len(items)}/{total}")

    entries = []
    tag = MovieTag.IMDB_TOP250
    for item in items:
        node = item["node"]

        rank = int(item["currentRank"])
        movie_id = node["id"]
        img_id = node["primaryImage"]["id"]
        video_id = node["latestTrailer"]["id"] if node["latestTrailer"] else ""

        link = f"{base_url}/title/{movie_id}/"
        title = node["titleText"]["text"]
        img = node["primaryImage"]["url"]
        year = int(str(node["releaseYear"]["year"])[:4])
        runtime = node["runtime"]["seconds"]
        rating = node["certificate"]["rating"] if node["certificate"] else ""
        genre = ",".join([v["genre"]["text"] for v in node["titleGenres"]["genres"]])
        score = str(node["ratingsSummary"]["aggregateRating"])
        count = str(node["ratingsSummary"]["voteCount"])
        outline = node["plot"]["plotText"]["plainText"]
        extra = {
            "imdb_url": link,
            "imdb_cover": img,
            "imdb_score": score,
            "imdb_vote": count,
            "imdb_image_id": img_id,
            "imdb_video_id": video_id,
            "imdb_rating": rating,
            "imdb_length": runtime,
            "imdb_summary": outline,
        }
        category = None
        region, director = None, None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, imdb_id=movie_id, **extra)
        entries.append(movie)
    return entries


def parse_imdb_page_list(page, **kwargs):
    # IMDb电影单解析
    base_url = kwargs["base_url"].rstrip("/")
    soup = BeautifulSoup(page, "html5lib")
    div_main = soup.body.find(id="main")
    if not div_main:
        return None, None

    div_pagi = div_main.find("div", class_="list-pagination")
    next_url = div_pagi.find(class_="next-page") if div_pagi else None
    if next_url:
        next_url = next_url["href"]
    logging.info(f"next url = {next_url}")

    div_lister = div_main.find("div", class_="lister-list")
    items = div_lister.find_all(class_="lister-item mode-detail")
    logging.debug(f"items = {len(items)}")
    entries = []
    tag = MovieTag.IMDB_LIST
    for item in items:
        img_part = item.find(class_="lister-item-image", recursive=False)
        con_part = item.find(class_="lister-item-content", recursive=False)
        desc_part = item.find(class_="list-description", recursive=False)

        href = img_part.a["href"].split("?")[0].lstrip("/")
        link = f"{base_url}/{href}"
        img = img_part.img["src"]
        title = img_part.img["alt"]

        idx = con_part.h3.find(class_="lister-item-index").text.strip(".")
        title2 = con_part.h3.a.text.strip()
        year = 0
        year_span = con_part.h3.find("span", class_="lister-item-year")
        if year_span:
            year = extract_year(year_span.text)

        # rating = con_part.find("span", "certificate")
        # length = con_part.find("span", "runtime")
        genre = strip(con_part.find("span", "genre").text)
        score = strip(con_part.find(class_="ipl-rating-star").text)
        t3 = con_part.find(class_="ratings-metascore")
        metascore = strip(t3.text) if t3 else ""
        info1 = [strip(v.text) for v in con_part.find_all("p", recursive=False)]
        info2 = [strip(v.text) for v in desc_part.find_all("p", recursive=False)]  # todo split by <br/>
        extra = {
            "imdb_url": link,
            "imdb_cover": img,
            "imdb_score": score,
            "metascore": metascore,
            "imdb_titles": [title2],
            "imdb_info": info1 + info2
        }
        category = None
        region = None
        director = None

        for line in info1:
            if "Director:" in line:
                director = dict([w.split(":") for w in line.split("|")]).get("Director", "").strip()
                break
        imdb_id = link.strip("/").split("title/")[-1] if link else None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=idx, imdb_id=imdb_id, **extra)
        entries.append(movie)
    return entries, next_url


def parse_imdb_page_detail(page, **kwargs):
    def _get_metadata_list(part):
        meta_list = part.find("ul", class_="ipc-metadata-list").find_all("li", recursive=False)
        result = []
        for meta in meta_list:
            key = meta.find("span", recursive=False)
            if not key:
                key = meta.a
            key = key.text
            if not meta.div:
                continue
            val = meta.div.find_all("li")
            if val:
                val = [li.a["href"] if li.svg else li.text for li in val]
            else:
                val = meta.div.text
            result.append([key, val])
        return result

    # def parse_imdb_page_detail(page, **kwargs):
    movie_id = kwargs.get("movie_id")

    soup = BeautifulSoup(page, "html5lib")
    head = soup.head
    url = head.find("meta", attrs={"property": "og:url"})["content"]
    if not movie_id:
        movie_id = head.find("meta", attrs={"property": "imdb:pageConst"})["content"]

    main = soup.body.main
    part1 = main.div.section.section  # "data-testid": "atf-wrapper-bg",
    part2 = main.div.section.find("div", recursive=False)
    if not (part1 and part2):
        logging.warning(f"Error imdb-movie-id = {movie_id}")
        return None

    title_part = part1.find("div", class_="sc-69e49b85-0")
    title = title_part.h1.text
    title_orig = title_part.find("div", class_="sc-d8941411-1")
    if title_orig:
        title_orig = title_orig.text.split("Original title:")[-1].strip()
    img_part = part1.find(class_="sc-e226b0e3-5")
    cover = img_part.img["src"]

    ul = title_part.find("ul", class_="ipc-inline-list")
    if "Episode" in part1.find("div", class_="sc-66ec1b32-1").text.strip() or \
            (ul and "TV Series" in ul.text.strip()):
        category = "tv"
        _, year, runtime = [li.text for li in ul.find_all("li")]
        rating = None  # 电影分级
    else:
        category = "movie"
        year, rating, runtime = [li.text for li in ul.find_all("li")]

    score_part = part1.find("div", class_="sc-69e49b85-1")
    score_info = score_part.find("div", attrs={"data-testid": "hero-rating-bar__aggregate-rating"})
    score = score_info.find("span", class_="sc-bde20123-1").text
    count = score_info.find("div", class_="sc-bde20123-3").text

    info_part = part1.find(class_="sc-e226b0e3-6")
    info_part_left = part1.find(class_="sc-e226b0e3-10")
    genres_part = info_part_left.find("div", attrs={"data-testid": "genres"})
    genres = [a.text for a in genres_part.find_all("a", class_="ipc-chip")]
    plot_part = info_part_left.find("p", attrs={"data-testid": "plot"})
    summary = plot_part.span.text
    info_result = _get_metadata_list(info_part_left)

    info_part_right = info_part.find("div", class_="sc-e226b0e3-11")
    stat_part = info_part_right.find("ul", class_="ipc-inline-list", recursive=False)
    li_list = stat_part.find_all("li", recursive=False)
    stats = [[li.find("span", class_=ckey).text for ckey in ["label", "score"]] for li in li_list]

    part2_div = part2.find("div", class_="sc-a83bf66d-1")

    rewards_part = part2_div.find("div", attrs={"data-testid": "awards"})
    top_rank = rewards_part.find("div", class_="sc-b45a339a-1")
    if top_rank:
        top_rank = top_rank.text.strip()
    rewards = _get_metadata_list(rewards_part)

    video_part = part2_div.find("section", attrs={"data-testid": "videos-section"})
    video_cnt = video_part.h3.span.text
    photo_part = part2_div.find("section", attrs={"data-testid": "Photos"})
    photo_cnt = photo_part.h3.span.text
    # review_part = part2_div.find("section", attrs={"data-testid": "UserReviews"})
    # review_cnt = review_part.h3.find("span", class_="ipc-title__subtext").text
    faq_part = part2_div.find("section", attrs={"cel_widget_id": "StaticFeature_FAQ"})
    faq_cnt = faq_part.h3.find("span", class_="ipc-title__subtext").text

    details = part2_div.find("section", attrs={"data-testid": "Details"})
    details_result = _get_metadata_list(details)
    box = part2_div.find("section", attrs={"data-testid": "BoxOffice"})
    box_result = _get_metadata_list(box) if box else []
    tech = main.find("section", attrs={"data-testid": "TechSpecs"})
    tech_result = _get_metadata_list(tech)

    info_dict = dict(stats + info_result + details_result + box_result + tech_result)
    used_keys = ["Director",  "Creator", "Writers",  "Stars",  "Release date", "Country of origin", "Countries of origin",  "Language",
                 "Also known as",  "Runtime",  "Metascore",  "Official sites", "User reviews", "Critic reviews"]
    director = info_dict.get("Director", info_dict.get("Creator"))
    writers = info_dict.get("Writers")
    actors = info_dict.get("Stars")
    release_date = info_dict.get("Release date")
    region = info_dict.get("Countries of origin", info_dict.get("Country of origin"))
    languages = info_dict.get("Language")
    title_alias = info_dict.get("Also known as")
    length = info_dict.get("Runtime")
    metascore = info_dict.get("Metascore")
    websites = info_dict.get("Official sites")
    extra = {key: val for key, val in info_dict.items() if key not in used_keys}

    imdb_url = url
    imdb_cover = cover
    imdb_rank = top_rank
    imdb_id = movie_id
    vote = count
    genre = " / ".join([v.strip() for v in genres])
    reviews = {k: info_dict.get(k) for k in ["User reviews", "Critic reviews"]}
    resources = {"video": video_cnt, "photo": photo_cnt}
    question = faq_cnt
    imdb = ImdbMovie(title,
                     category,
                     year,
                     region,
                     director,
                     genre,
                     imdb_url,
                     imdb_cover,
                     imdb_rank,
                     imdb_id,
                     writers,
                     actors,
                     languages,
                     release_date,
                     websites,
                     length,
                     title_alias,
                     title_orig,
                     score,
                     vote,
                     metascore,
                     rating,
                     summary,
                     resources,
                     rewards,
                     reviews,
                     question,
                     **extra)
    tag = MovieTag.IMDB_DETAIL
    movie = Movie(title, category, year, region, director, genre, tag=tag, imdb=imdb)
    return movie
