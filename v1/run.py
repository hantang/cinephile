import argparse
import logging
import time
import traceback
from pathlib import Path

from crawlers import (
    DoubanCrawler,
    ImdbCrawler,
    MaoyanCrawler,
    MtimeCrawler,
    TmdbCrawler,
    DoubanWeeklyCrawler,
)
from utils import get_table, get_dt

BASEDIR = ".."
SITES = ["douban", "imdb", "mtime", "maoyan", "tmdb"]
EXTRAS = ["douban-weekly"]


def download_stats(savedir, sites, retry=2):
    stats = {}
    savedir = "{}/{}/".format(BASEDIR, savedir.split("./")[-1].strip("/"))
    for site in sites:
        logging.info("process:\n" + "\n".join(["=" * 50, " " * 20 + site, "=" * 50]))

        crawler, result = None, ""
        if site == "douban":
            crawler = DoubanCrawler(savedir + "douban", request_option="curl_cffi")
        elif site == "imdb":
            crawler = ImdbCrawler(savedir + "imdb", request_option="requests")
        elif site == "mtime":
            crawler = MtimeCrawler(savedir + "misc", request_option="requests")
        elif site == "maoyan":
            crawler = MaoyanCrawler(savedir + "misc", request_option="requests")
        elif site == "tmdb":
            crawler = TmdbCrawler(savedir + "misc", request_option="curl_cffi")
        elif site == "douban-weekly":
            crawler = DoubanWeeklyCrawler(savedir + "douban-weekly")

        for i in range(retry):
            try:
                if crawler:
                    count, result = crawler.process()
                    logging.info(f"result = {count}\n\n")
                    if result:
                        stats[site] = result
                        break
                    elif count != -2:
                        time.sleep(30)
            except:
                traceback.print_exc()
                if i + 1 < retry:
                    time.sleep(30)
    return stats


def update_readme(stats):
    readfile = Path(f"{BASEDIR}/README.md")
    hr_line = "-" * 3
    limit = 2
    raw_readmes = []
    if readfile.exists():
        with open(readfile) as f:
            raw_readmes = f.readlines()[:limit]
    raw_readmes += ["\n" * max(0, limit - len(raw_readmes))]
    logging.info(f"readme = {raw_readmes}")

    logging.info("create table, part1")
    part1 = []
    for site in EXTRAS:
        if site not in stats:
            continue

        data = stats[site]
        desc, items = data["desc"], data["items"]
        logging.info(f"table {site}, desc={desc}")

        table = []
        for entry in items:
            subdesc, subitems = entry["desc"], entry["items"]
            table.append([subdesc] + subitems)
        md_table = get_table(table)
        part1 += [f"## {desc}", md_table]

    logging.info("create table, part2")
    table2 = []
    for site in SITES:
        if site not in stats:
            continue
        data = stats[site]
        desc, items = data["desc"], data["items"]
        table2.append([desc] + items)
        logging.info(f"table {site}, desc={desc}")
    if table2:
        md_table2 = get_table(table2)
        part2 = ["## 电影Top榜单", md_table2]
    else:
        part2 = []

    md_out = ["".join(raw_readmes).strip(), "最近更新：{}".format(get_dt())]
    if part1:
        md_out += [hr_line] + part1
    if part2:
        md_out += [hr_line] + part2

    logging.info(f"save to {readfile}")
    with open(readfile, "w") as fw:
        fw.write("\n\n".join(md_out) + "\n")
    logging.info("done")


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

    stats = download_stats(args.savedir, args.sites)
    if len(stats) > 0:
        update_readme(stats)
    logging.info(f"done\n")
