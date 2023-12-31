import sys

sys.path.append("src/")

import logging
from cinephile.utils.misc import set_logging
from cinephile.crawlers import DoubanCrawler
from cinephile.crawlers.imdb import ImdbCrawler
from cinephile.crawlers.mtime import MtimeCrawler
from cinephile.crawlers.maoyan import MaoyanCrawler
from cinephile.crawlers.tmdb import TmdbCrawler
from cinephile.crawlers.imdbhist import ImdbHistCrawler
from cinephile.crawlers.listchallenges import ListChallengesCrawler


def run_douban(save_dir):
    logging.info("Test douban")
    crawler = DoubanCrawler(save_dir)
    crawler.process_top250(savedir=save_dir)
    # crawler.process_detail(movie_id=iii, savedir=save_dir)
    # crawler.process_list(movie_list_id=jjj, savedir=save_dir, page_limit=1)
    # crawler.process_hot(savedir=save_dir)
    # for year in range(2014, 2024):
    #     crawler.process_annual(year=year, savedir=save_dir)
    # crawler.process_annual(year=2014, savedir=save_dir)


def run_imdb(save_dir):
    crawler = ImdbCrawler(save_dir)
    # crawler.process_top250()
    # mlid = "ls523837749"
    # crawler.process_list(movie_list_id=mlid, page_limit=-1)
    # crawler.process_detail(movie_id="tt0106332")

    crawler = ImdbHistCrawler(save_dir)
    # crawler.query_hist(year_month="202301")
    # crawler.process_hist_top250(date="20230107")


def run_more(save_dir):
    crawler = MtimeCrawler(save_dir)
    # crawler.process_top100()
    # crawler.process_detail(movie_id=274783)

    crawler = MaoyanCrawler(save_dir)
    # crawler.process_top100()
    # crawler.process_detail(movie_id="1458876")

    crawler = TmdbCrawler(save_dir)
    # crawler.process_top250()
    # crawler.process_detail(movie_id="https://www.themoviedb.org/movie/129")
    # crawler.process_detail(movie_id="230835", mtype="tv")
    # crawler.process_detail(movie_id=278, mtype="movie")

    crawler = ListChallengesCrawler(save_dir)
    # url = "https://www.listchallenges.com/1001-movies-2003-2021-chronological"
    # crawler.process_list(movie_list_id=url, page_start=10, page_limit=12)


if __name__ == "__main__":
    set_logging()
    save_dir = "temp/douban-data"
    # run_douban(save_dir)
    save_dir = "temp/imdb-data"
    # run_imdb(save_dir)
    save_dir = "temp/misc-data"
    # run_more(save_dir)
