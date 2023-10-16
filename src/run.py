import argparse
import datetime
import logging
from pathlib import Path
import traceback

from crawlers import (
    DoubanCrawler,
    ImdbCrawler,
    MaoyanCrawler,
    MtimeCrawler,
    TmdbCrawler,
    DoubanWeeklyCrawler,
)

BASEDIR = ".."
SITES = ["douban", "imdb", "mtime", "maoyan", "tmdb"]
EXTRAS = ["douban-weekly"]


def download(savedir, sites):
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

        try:
            if crawler:
                count, result = crawler.process()
                logging.info(f"result = {count}\n\n")
                if result:
                    stats[site] = result
        except:
            traceback.print_exc()
    return stats


def create_md_table(table, index=True):
    sep = " | "
    min_len = 2
    row_cnt = max([len(col) for col in table])
    header = ["**{}**".format(col[0]) for col in table]
    if index:
        header = ["**index**"] + header
    lines = [
        sep.join(header),
        sep.join([":{}:".format("-" * min(len(h), min_len)) for h in header]),
    ]
    for i in range(1, row_cnt):
        row = []
        for col in table:
            if i >= len(col):
                text = " " * min_len
            else:
                cell = col[i]
                if isinstance(cell, list):
                    img = f"![img]({cell[0]})" + "<br/>"
                    alt = cell[1]
                else:
                    img = ""
                    alt = cell
                text = img + alt + " " * max(0, min_len - len(alt))
            row.append(text)
        if index:
            row = [f"{i:3d}"] + row
        lines.append(sep.join(row))
    lines = [f"|{line}|" for line in lines]

    return "\n".join(lines)


def readme(dt, stats):
    readfile = Path(f"{BASEDIR}/README.md")
    hr_line = "-" * 3
    limit = 2
    temp = []
    if readfile.exists():
        with open(readfile) as f:
            temp = f.readlines()[:limit]
    temp += ["\n" * max(0, limit - len(temp))]
    first = "".join(temp)
    logging.info(first)

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
        md_table = create_md_table(table)
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
    md_table2 = create_md_table(table2)
    part2 = ["## 电影Top榜单", md_table2]

    md_out = (
        [
            first,
            "Last update: {}".format(dt.strftime("%Y-%m-%dT%H:%M:%SZ")),
            hr_line,
        ]
        + part1
        + [hr_line]
        + part2
    )

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

    dt = datetime.datetime.utcnow()
    stats = download(args.savedir, args.sites)
    if len(stats) > 0:
        readme(dt, stats)
    logging.info(f"done\n")
