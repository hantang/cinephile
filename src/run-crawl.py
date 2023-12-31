import argparse
import logging
import time
import traceback

from cinephile.crawlers import (
    DoubanCrawler,
    ImdbCrawler,
    MaoyanCrawler,
    MtimeCrawler,
    TmdbCrawler,
)
from cinephile.utils.misc import set_logging

BASEDIR = ".."
SITES = ["douban", "imdb", "mtime", "maoyan", "tmdb"]
EXTRAS = ["douban-weekly"]


def download_stats(savedir, sites, retry=2):
    stats = {}
    savedir = "{}/{}/".format(BASEDIR, savedir.split("./")[-1].strip("/"))
    result, result_file = None, None
    for site in sites:
        logging.info("process:\n" + "\n".join(["=" * 50, " " * 20 + site, "=" * 50]))
        crawler, result = None, ""
        for i in range(retry):
            try:
                if site == "douban":
                    crawler = DoubanCrawler()
                    result, result_file = crawler.process_top250(savedir + "douban")
                elif site == "douban-weekly":
                    crawler = DoubanCrawler()
                    result, result_file = crawler.process_hot(savedir + "douban-weekly")
                elif site == "imdb":
                    crawler = ImdbCrawler()
                    result, result_file = crawler.process_top250(savedir + "imdb")
                elif site == "mtime":
                    crawler = MtimeCrawler()
                    result, result_file = crawler.process_top100(savedir + "misc")
                elif site == "maoyan":
                    crawler = MaoyanCrawler()
                    result, result_file = crawler.process_top100(savedir + "misc")
                elif site == "tmdb":
                    crawler = TmdbCrawler()
                    result, result_file = crawler.process_top250(savedir + "misc")
                logging.info(f"site = {site}, result = {result}, result_file={result_file}\n")
                if (result > 0 or result == -2) and result_file:
                    stats[site] = (result, result_file)
                    break
            except:
                traceback.print_exc()
                if i + 1 < retry:
                    logging.info("time to sleep")
                    time.sleep(30)
    return stats


if __name__ == "__main__":
    set_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--savedir", type=str, help="save dir", default="../data")
    parser.add_argument("--sites", nargs="+", type=str, help="List of movie sites", required=True)
    args = parser.parse_args()
    logging.info(f"args = {args}\n")

    stats = download_stats(args.savedir, args.sites)
    # if len(stats) > 0:
    #     update_readme(stats)
    logging.info(f"done\n")
