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
MISCDIR = "misc"
MAIN_SITES = ["douban", "imdb"]
EXTRA_SITES = ["douban-weekly"]
crawler_dict = {
    "douban": DoubanCrawler,
    "imdb": ImdbCrawler,
    "mtime": MtimeCrawler,
    "maoyan": MaoyanCrawler,
    "tmdb": TmdbCrawler,
    "douban-weekly": DoubanCrawler,
}


def download_stats(savedir, sites, retry=2):
    savedir = "{}/{}/".format(BASEDIR, savedir.split("./")[-1].strip("/"))
    result_set = []
    for site in sites:
        logging.info("process:\n" + "\n".join(["=" * 50, " " * 20 + site, "=" * 50]))
        if site not in crawler_dict:
            logging.warning(f"Ignore: {site}")
            continue

        crawler = crawler_dict[site]()
        for i in range(retry):
            try:
                subsavedir = savedir + (site if site in MAIN_SITES + EXTRA_SITES else MISCDIR)
                if site in EXTRA_SITES:
                    result, result_file = crawler.process_hot(subsavedir)
                else:
                    result, result_file = crawler.process_top(subsavedir)

                logging.info(f"Site = {site}, result = {result}, result_file={result_file}\n")
                if (result > 0 or result == -2) and result_file:
                    result_set.append(result_file)
                    break
            except Exception:
                traceback.print_exc()
                if i + 1 < retry:
                    logging.info("time to sleep")
                    time.sleep(30)

        files = "\n- ".join(map(str, result_set))
        logging.info(f"Result = {len(result_set)}/{len(sites)}:\n- {files}")


if __name__ == "__main__":
    set_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--savedir", type=str, help="save dir", default=f"{BASEDIR}/data")
    parser.add_argument("--sites", nargs="+", type=str, help="List of movie sites", required=True)
    args = parser.parse_args()
    logging.info(f"args = {args}\n")

    download_stats(args.savedir, args.sites)
    logging.info(f"done\n")
