import argparse
import json
import logging
from pathlib import Path

from cinephile.crawlers import (
    DoubanCrawler,
    ImdbCrawler,
    MaoyanCrawler,
    MtimeCrawler,
    TmdbCrawler,
)
from cinephile.utils import datetimes
from cinephile.utils.movies import MovieCluster

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

    texts = [
        "".join(raw_readmes).strip(),
        "最近更新：{}".format(datetimes.time2zh())
    ]
    is_first = True
    for key in EXTRAS:
        file = Path(stats[key][1])
        if not file.exists():
            continue
        logging.info(f"read file {file}")
        with open(file) as f:
            data = json.load(f)
        movie_cluster = MovieCluster.from_json(data)
        desc = movie_cluster.description
        df = movie_cluster.to_df(link=True, img=True)
        if df is not None:
            if is_first:
                texts.append(hr_line)
            logging.info(f"add {desc}, shape={df.shape}")
            texts.extend(["## {}".format(desc), df.to_markdown()])
            is_first = False

    cluster = []
    link_tag = []
    for key in SITES:
        if key not in stats:
            continue
        file = Path(stats[key][1])
        if not file.exists():
            continue
        if key in SITES[:2]:
            link_tag.append(len(cluster))
        logging.info(f"read file {file}")
        with open(file) as f:
            data = json.load(f)
        mc = MovieCluster.from_json(data)
        logging.info(f"movie cluster = {mc.description}, movies = {len(mc.get_movies())}")
        cluster.append(mc)
    desc = "电影Top榜单"
    movie_cluster = MovieCluster("", "", desc, "", cluster=cluster)
    df = movie_cluster.to_df(link=link_tag, img=False)
    if df is not None:
        logging.info(f"add {desc}, shape={df.shape}")
        texts.extend([hr_line, "## {}".format(desc), df.to_markdown()])

    logging.info(f"save to {readfile}")
    with open(readfile, "w") as fw:
        fw.write("\n\n".join(texts) + "\n")
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
