import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from cinephile.utils import datetimes
from cinephile.utils.misc import set_logging
from cinephile.utils.movies import MovieCluster

BASEDIR = ".."
MISCDIR = "misc"
SITES = ["douban", "imdb", "mtime", "maoyan", "tmdb"]
MAIN_SITES = ["douban", "imdb"]
EXTRA_SITES = ["douban-weekly"]


def _get_top_stats(datadir, moredir, name, desc=""):
    files = []
    for site in name:
        file = None
        for basedir in [datadir, moredir]:
            tmpdir = Path(basedir, site if site in MAIN_SITES else MISCDIR)
            if not tmpdir.exists(): continue
            datafiles = list(tmpdir.glob(f"{site}*.json"))
            if datafiles:
                datafiles = sorted(datafiles, reverse=True, key=lambda x: x.stem.split("-v")[-1])
                file = datafiles[0]  # use latest
                break
        if file:
            files.append(file)
        else:
            logging.warning(f"Empty file in {site}: datadir={datadir}")
    if len(files) == 0:
        logging.warning("files are empty")
        return []

    data_list = []
    urls = []
    for file in files:
        logging.info(f"read file = {file}")
        with open(file) as f:
            data = json.load(f)
        data_list.append(data)
        url_hits = [v in file.name for v in MAIN_SITES]
        urls.append(True if any(url_hits) else False)

    mc = MovieCluster.merge_from_json(*data_list)
    df = mc.to_df_table(keep_url=urls, keep_cover=False)
    part = [(desc, df)]
    return part


def _get_extra_stats(datadir, moredir, names):
    files = []
    for site in names:
        for basedir in [datadir, moredir]:
            tmpdir = Path(basedir, site)
            if not tmpdir.exists(): continue
            datafiles = list(tmpdir.glob(f"*.json"))
            if datafiles:
                datafiles = sorted(datafiles, reverse=True, key=lambda x: x.stem.split("-v")[-1])
                files.append(datafiles[0])
    if len(files) == 0:
        logging.warning("files are empty")
        return []

    part = []
    for file in files:
        logging.info(f"read file = {file}")
        with open(file) as f:
            data = json.load(f)
        mc = MovieCluster.from_json(data)
        df = mc.to_df_table(keep_url=True, keep_cover=True, split_cover=True)
        desc = mc.description
        part.append((desc, df))
    return part


def _get_diff_stats(datadir, names, desc_list, count_list):
    parts = []
    for i, site in enumerate(names):
        desc = desc_list[i]
        count = max(count_list[i], 2)

        tmpdir = Path(datadir, site)
        if not tmpdir.exists(): continue
        datafiles = tmpdir.glob(f"{site}*.json")
        datafiles = sorted(datafiles, reverse=True, key=lambda x: x.stem.split("-v")[-1])
        files = datafiles[:count]
        if len(files) <= 1: continue

        cols = [site + "_id", "rank", "title", "url"]
        key_col = cols[0]
        rank_col = cols[1]
        title_col = cols[2]
        url_col = cols[3]

        df_list = {}
        for file in files:
            with open(file) as f:
                data = json.load(f)
            mc = MovieCluster.from_json(data)
            dt = mc.release_time.split(" ")[0]
            df = mc.to_df()[cols]
            df[title_col] = df[[title_col, url_col]].apply(
                lambda x: "[{}]({})".format(x[title_col], x[url_col]) if x[url_col] else x[title_col], axis=1)
            df_list[dt] = df[cols[:3]].fillna("").astype(str)

        dates = sorted(df_list.keys())
        df_merge = None
        id2titles = {}
        for dt in dates:
            dfx = df_list[dt]
            dfx2 = dfx[[key_col, rank_col]].rename(columns={rank_col: dt})
            if df_merge is None:
                df_merge = dfx2
            else:
                df_merge = df_merge.merge(dfx2, how="outer", on=key_col)
            titles = dfx[[key_col, title_col]].set_index(key_col).to_dict()[title_col]
            id2titles.update(titles)
        df_merge[dates] = df_merge[dates].fillna("-").astype(str)
        df_merge["update"] = df_merge.apply(
            lambda x: any([x[v] != x[dates[0]] for v in dates[1:]]), axis=1)
        df_out = df_merge[df_merge["update"]]
        # if not df_out.empty:
        df_title = pd.Series(id2titles).reset_index()
        df_title.columns = [key_col, title_col]
        df_out = df_out.merge(df_title, on=key_col)[[title_col] + dates]
        parts.append((desc, df_out))

    return parts


def update_readme(basedir, moredir, limit = 3):
    readfile = Path(f"{BASEDIR}/README.md")
    hr_line = "-" * 3
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
    
    extra_parts = _get_extra_stats(basedir, moredir, EXTRA_SITES)
    diff_parts = _get_diff_stats(basedir, MAIN_SITES, desc_list=["豆瓣Top250调整", "IMDb Top250调整"], count_list=[5, 2])
    top_parts = _get_top_stats(basedir, moredir, SITES, desc="电影Top榜单")
    toc = ["- Table of Contents"]
    texts2 = []
    for part in [extra_parts, diff_parts, top_parts]:
        texts2.append(hr_line)
        for desc, df in part:
            if df is not None:
                logging.info(f"add {desc}, shape={df.shape}")
                if desc:
                    desc = desc.strip()
                    desc2 = desc.lower().replace(" ", "-")
                    toc.append(f"  - [{desc}](#{desc2})")
                    texts2.append(f"## {desc}")
                texts2.append(df.to_markdown())
    texts.append("\n".join(toc))
    readfile2 = readfile
    logging.info(f"save to {readfile2}")
    with open(readfile2, "w") as fw:
        fw.write("\n\n".join(texts + texts2) + "\n")
    logging.info("done")


if __name__ == "__main__":
    set_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--datadir", type=str, help="data dir", default=f"{BASEDIR}/data")
    args = parser.parse_args()
    logging.info(f"args = {args}\n")
    update_readme(args.datadir, moredir=f"{BASEDIR}/archive")
    logging.info(f"done\n")
