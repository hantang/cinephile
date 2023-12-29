import sys

sys.path.append("src/")

from cinephile.utils.misc import set_logging
from cinephile.crawlers import DoubanCrawler
from cinephile.crawlers.imdb import ImdbCrawler

from cinephile.crawlers.mtime import MtimeCrawler
from cinephile.crawlers.maoyan import MaoyanCrawler
from cinephile.crawlers.tmdb import TmdbCrawler
from cinephile.crawlers.misc import ImdbHistCrawler, ListChallengesCrawler


def run_douban(save_dir):
    crawler = DoubanCrawler(save_dir)
    # crawler.process_top250(savedir=save_dir)
    # crawler.process_top250_v2(savedir=save_dir)
    # crawler.process_detail(movie_id=35256092, savedir=save_dir)
    # crawler.process_list(movie_list_id=1868211, savedir=save_dir, page_limit=10)
    # crawler.process_hot(savedir=save_dir)


def run_imdb(save_dir):
    crawler = ImdbCrawler(save_dir)
    # crawler.process_top250()
    # mlid = 'ls090483548'
    # crawler.process_list(movie_list_id=mlid, page_limit=-1)

    crawler = ImdbHistCrawler(save_dir)
    # crawler.query_hist(year_month="202301")
    # crawler.process_hist_top250(date="20230107")


def run_more(save_dir):
    crawler = MtimeCrawler(save_dir)
    # out = crawler.process()
    # print(f"out = {out}")
    # out = crawler.process_top100()
    # print(out, flush=True)
    # out = crawler.process_detail(movie_id=274783)
    # print(out)

    crawler = MaoyanCrawler(save_dir)
    # crawler.process_top100()

    crawler = TmdbCrawler()
    # crawler.process_top250(save_dir)

    crawler = ListChallengesCrawler(save_dir)
    # url = 'https://www.listchallenges.com/1001-movies-2003-2021-chronological'
    # crawler.process_list(movie_list_id=url, page_start=10)


def run_douban_annual(save_dir):
    crawler = DoubanCrawler()
    # for year in range(2015, 2023):
    #     crawler.process_annual(year=year, savedir=save_dir)
    # crawler.process_annual(year=2014, savedir=save_dir)


if __name__ == "__main__":
    set_logging()
    save_dir = "data/douban-annual"
    run_douban_annual(save_dir)

