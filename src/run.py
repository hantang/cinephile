import argparse
import logging

from crawlers import DoubanCrawler, ImdbCrawler, MaoyanCrawler, MtimeCrawler


def download(savedir, sites):
    stats = {}
    for site in sites:
        logging.info("process:\n" + "\n".join(["=" * 50, " " * 20 + site, "=" * 50]))

        crawler, result = None, ""
        if site == "douban":
            crawler = DoubanCrawler(savedir, request_option="curl_cffi")
        elif site == "imdb":
            crawler = ImdbCrawler(savedir, request_option="requests")
        elif site == "mtime":
            crawler = MtimeCrawler(savedir, request_option="requests")
        elif site == "maoyan":
            crawler = MaoyanCrawler(savedir, request_option="requests")

        if crawler:
            result = crawler.process()
        logging.info(f"result = {result}\n\n")
        stats[site] = result
    return stats


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(filename)s [line:%(lineno)d] %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--savedir", type=str, help="save dir", default="../data")
    parser.add_argument(
        "--sites", nargs="+", type=str, help="List of movie sites", required=True
    )
    args = parser.parse_args()
    logging.info(f"args = {args}\n")

    stats = download(args.savedir, args.sites)
    logging.info(f"done, stats = {stats}\n")
