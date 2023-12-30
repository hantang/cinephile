import logging

from bs4 import BeautifulSoup

from cinephile.utils.movies import Movie, MovieTag
from cinephile.utils.texts import strip, extract_year


def parse_tmdb_page_top_lang(page, **kwargs):
    soup = BeautifulSoup(page, "html.parser")
    logging.info("Title = {}".format(soup.title.text.strip()))

    div_content = soup.body.find("div", class_="content_wrapper")
    div_page = div_content.find("div", class_="page_wrapper")
    if not div_page:
        return None
    next_url = div_page.find("p", class_="load_more").a["href"]
    items_raw = div_page.find_all("div", class_="card")
    items = [item for item in items_raw if " ".join(item["class"]) == "card style_1"]
    logging.info(f"items = {len(items)}/{len(items_raw)}")
    titles = [strip(item.find("div", class_="content").h2.text) for item in items]
    logging.info(f"next url = {next_url}")
    return titles, next_url


def parse_tmdb_page_top(page, **kwargs):
    start = kwargs["start"]
    base_url = kwargs["base_url"]
    titles = kwargs["titles"]

    soup = BeautifulSoup(page, "html.parser")
    div_content = soup.body.find("div", class_="content_wrapper")
    div_page = div_content.find("div", class_="page_wrapper")
    if not div_page:
        return None
    items_raw = div_page.find_all("div", class_="card")
    items = [item for item in items_raw if " ".join(item["class"]) == "card style_1"]
    logging.info(f"items = {len(items)}/{len(items_raw)}")
    next_url = div_page.find("p", class_="load_more").a["href"]

    entries = []
    tag = MovieTag.TMDB_TOP
    for i, item in enumerate(items):
        rank = start + i + 1
        div_image = item.find("div", class_="image")
        tmdb_id = div_image.a["href"].strip().split("?")[0]
        link = base_url + tmdb_id
        img = base_url + div_image.img["src"].strip()
        tmdb_id = tmdb_id.strip("/").split("/")[-1]

        div_content = item.find("div", class_="content")
        title = strip(div_content.h2.text)
        date = strip(div_content.p.text)
        year = date.split(",")[-1].strip()[:4]
        if year.isdigit():
            year = int(year)
        else:
            logging.warning(f"Error year {title}, {year}")
            year = 0
        score = div_content.find("div", class_="user_score_chart")["data-percent"]
        more = {
            "tmdb-url": link,
            "tmdb-cover": img,
            "tmdb-id": tmdb_id,
            "tmdb-score": score,
            "tmdb-date": date,
        }
        if titles:
            more["tmdb-titles"] = [titles[i]]
        category = None
        region, director, genre = None, None, None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, **more)
        entries.append(movie)

    return entries, next_url


def parse_tmdb_page_detail(page, **kwargs):
    base_url = kwargs["base_url"].rstrip("/") + "/"

    soup = BeautifulSoup(page, "html5lib")
    logging.info("Process movie = {}".format(strip(soup.title.text)))

    main_part = soup.body.main
    # part1 = main_part.find(class_="header")
    part1 = main_part.find(id="original_header")
    part2 = main_part.find(id="media_v4")

    img_part = part1.find(class_="poster")
    alt = img_part.img["alt"]
    img = base_url + img_part.img["src"]

    head_part = part1.find(class_="header poster")
    title_part = head_part.find(class_="title")
    href = strip(title_part.h2.a["href"])
    link = base_url + href
    title = strip(title_part.h2.a.text)
    year = extract_year(title_part.h2.find("span", class_="release_date").text)
    facts = title_part.find(class_="facts")
    rating = facts.find("span", class_="certification")
    if rating:
        rating = strip(rating.text)
    release_date = facts.find("span", class_="release")
    if release_date:
        release_date = strip(release_date.text)
    genre = facts.find("span", class_="genres")
    if genre:
        genre = strip(genre.text)
    length = facts.find("span", class_="runtime")
    if length:
        length = strip(length.text)
    score = strip(head_part.find("div", class_="user_score_chart")["data-percent"])
    header_info = head_part.find(class_="header_info")
    tagline = strip(header_info.h3.text)
    overview = strip(header_info.find(class_="overview").text)
    info1 = [[strip(li.find("p", class_="character").text), strip(li.p.text)] for li in
             header_info.find_all("li", class_="profile")]

    left_part = part2.find(class_="white_column")
    right_part = part2.find(class_="grey_column")
    facts = right_part.find("section", class_="facts")
    keywords = right_part.find("section", class_="keywords")
    social_links = facts.find(class_="social_links").a
    website = social_links["href"] if social_links else None
    plist = facts.find_all("p", recursive=False)
    info2 = []
    for p in plist:
        if not p.strong:
            continue
        key = p.strong.text
        p.strong.decompose()
        val = p.text
        info2.append([strip(key), strip(val)])

    keywords = [strip(li.text) for li in keywords.find_all("li")]
    left_part.find("section", class_="top_billed")
    cast_part = left_part.find("section", class_="top_billed").find_all("li")
    actors = [[strip(li.p.a.text), strip(li.find("p", class_="character").text)] for li in cast_part if
              li.find("p", class_="character")]
    review_part = left_part.find("section", class_="review").find_all("li")
    reviews = []
    for li in review_part:
        lia = li.a
        if not lia.span: continue
        val = lia.span.text
        lia.span.decompose()
        key = lia.text
        reviews.append([strip(key), strip(val)])
    media_part = left_part.find("section", class_="panel media_panel media scroller")
    if not media_part:
        media_part = left_part.find("section", class_='panel media_panel media tv_panel scroller')
    media_part = media_part.find_all("li")
    resources = []
    for li in media_part:
        lia = li.a
        if li and lia and lia.span:
            val = lia.span.text
            lia.span.decompose()
            key = lia.text
            resources.append([strip(key), strip(val)])

    extra = {
        "tmdb-cover": img,
        "tmdb-url": link,
        "tmdb-score": score,
        "tmdb-comment": tagline,
        "tmdb-summary": overview,
        "tmdb-titles": alt,
        "tmdb-release-date": release_date,
        "tmdb-length": length,
        "tmdb-rating": rating,
        "tmdb-website": website,
        "tmdb-info": info1 + info2,
        "tmdb-keywords": keywords,
        "tmdb-actors": actors,
        "tmdb-reviews": reviews,
        "tmdb-resources": resources,
    }
    tag = MovieTag.TMDB_DETAIL
    # category = "tv" if left_part.find("section", class_="panel season") else "movie"
    category = href.strip("/").split("/")[0].strip()  # tv or movie
    region = None
    director = []
    for k, v in info1:
        k = k.lower()
        if "director" in k or "creator" in k:
            director.append(v)
    movie = Movie(title, category, year, region, director, genre, tag=tag, **extra)
    return movie
