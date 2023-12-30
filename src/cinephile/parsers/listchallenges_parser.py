import logging
import re

from bs4 import BeautifulSoup

from cinephile.utils.movies import Movie, MovieTag
from cinephile.utils.texts import strip


def extract_listchallenges_page_info(page, desc=None):
    logging.info("extract paginator: {} ...".format(desc if desc else ""))
    soup = BeautifulSoup(page, "html5lib")
    logging.info("Title = {}".format(strip(soup.title.text)))

    div_content = soup.body.find(id='listMasterContentWrapper')
    div_pagi = div_content.find(id='MainContent_MainContent_pager')
    more_hrefs = [a['href'] for a in div_pagi.find_all(['a'])]

    div_top = soup.body.find(class_='content listMaster-top')
    h1 = div_top.h1.text.strip()
    about = div_top.find(id='MainContent_divDescription').text.strip()
    div_info = div_top.find(class_='listMaster-topInfo')
    div_div = div_info.find_all('div', recursive=False)
    info = [strip(v.text.strip()) for dv in div_div for v in dv.find_all('div', recursive=False)]
    author = "\n".join(info)
    list_desc = {"name": h1, "author": author, "about": about}
    total_num = int(info[2].split("of")[-1].split("(")[0])
    return more_hrefs, total_num, list_desc


def parse_listchallenges_page_list(page, **kwargs):
    # list challenges电影单解析
    base_url = kwargs["base_url"].rstrip("/")
    total = kwargs.get('total', 40)
    soup = BeautifulSoup(page, "html5lib")
    div_content = soup.body.find(id='listMasterContentWrapper')
    if not div_content:
        return None
    div_list = div_content.find(id='repeaterListItems')

    items = div_list.find_all('div', class_='list-item', recursive=False)
    logging.debug(f"items = {len(items)} / {total}")
    entries = []
    tag = MovieTag.LC_LIST
    for item in items:
        rank = item.find(class_='item-rank').text.strip()
        name_alt = item.img['alt']
        img = "{}/{}".format(base_url, item.img['src'].lstrip("/"))
        item_name = item.find(class_='item-name').text.strip()
        item_name_out = re.findall(r'(.+) \(([12]\d{3})\)', item_name)
        title, year = None, 0
        if item_name_out:
            title, year = item_name_out[0]
            if '(' in title:
                title_tmp = re.findall(r'(.+) \(([12]\d{3})\)', title)
                if title_tmp:
                    title = title_tmp[0][0]
        rt = item.find(class_='rt-score')
        if rt.a:
            link = rt.a['href']
            rt_score = rt.text.strip().split()[-1]  # rt: rotten tomatoes
        else:
            link, rt_score = None, None
        more = {
            "listchallenges_rt_url": link,
            "listchallenges_rt_cover": img,
            "listchallenges_rt_score": rt_score,
            "listchallenges_titles": [name_alt]
        }
        category = None
        region, director, genre = None, None, None
        movie = Movie(title, category, year, region, director, genre, tag=tag, rank=rank, **more)
        entries.append(movie)
    return entries
