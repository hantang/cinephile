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
    part = [[desc, df]]
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
        part.append([desc, df])
    return part


def _get_diff_stats(datadir, moredir, names, desc_list, count_list):
    # 统计top250名单变化
    parts = []
    min_count = 2
    for i, site in enumerate(names):
        desc = desc_list[i]
        count = max(count_list[i], min_count)
        logging.info(f"Process {site}, {desc} trending")
        datafiles = []
        for basedir in [datadir, moredir]:
            tmpdir = Path(basedir, site)
            if not tmpdir.exists(): continue
            datafiles.extend(tmpdir.glob(f"{site}*.json"))
        datafiles = sorted(datafiles, reverse=True, key=lambda x: x.stem.split("-v")[-1])
        files = datafiles[:count]
        logging.info(f"files = {len(datafiles)} / {len(files)}, max count = {count}")
        if len(files) < min_count: continue

        rank_col = "rank"
        title_col = "title_markdown"
        url_col = "url"
        id_col = site + "_id"
        score_col = site + "_score"
        vote_col = site + "_vote"
        title_col2 = "电影"
        score_col2 = "Top250电影评价（平均）"
        vote_col2 = "Top250电影评价人数（平均）"
        cols = [id_col, rank_col, title_col, url_col, score_col, vote_col]

        df_list = {}
        files = sorted(files)
        for file in files:
            with open(file) as f:
                data = json.load(f)
            mc = MovieCluster.from_json(data)
            dt = mc.release_time.split(" ")[0]
            if dt not in df_list:
                df = mc.to_df()[cols].copy()
                df_list[dt] = df

        dates = sorted(df_list.keys())
        logging.info(f"Dates = {dates}")
        # if len(dates) <= min_count: continue
        df_id_rank = None
        score_list = []
        vote_list = []
        id2titles_dict = {}
        for dt in dates:
            dfx = df_list[dt]
            dfx2  = dfx[[id_col, rank_col]].copy()
            dfx2 = dfx2.rename(columns={rank_col: dt})
            if df_id_rank is None:
                df_id_rank = dfx2
            else:
                df_id_rank = df_id_rank.merge(dfx2, how="outer", on=id_col)
            score_list.append(dfx[score_col])
            vote_list.append(dfx[vote_col])
            titles = dfx[[id_col, title_col]].set_index(id_col).to_dict()[title_col]
            id2titles_dict.update(titles)

        df_score = pd.concat(score_list, axis=1)
        df_score.columns = dates
        df_score = df_score.fillna(0.).astype(float)
        df_score_mean = df_score.mean(axis=0)

        df_vote = pd.concat(vote_list, axis=1)
        df_vote.columns = dates
        df_vote = df_vote.fillna(0).astype(int)
        df_vote_mean = df_vote.mean(axis=0)
        df_stats = pd.concat([df_score_mean, df_vote_mean], axis=1)
        df_stats.columns = [score_col2, vote_col2]
        df_stats[score_col2] = df_stats[score_col2].apply(lambda x: f"{float(x):.4f}")
        df_stats[vote_col2] = df_stats[vote_col2].apply(lambda x: f"{float(x):.2f}")
        logging.info(f"score/vote stats = {df_stats.shape}")

        # 统计排名出现变化的电影
        df_id_rank[dates] = df_id_rank[dates].fillna("-").astype(str)
        df_id_rank["update"] = df_id_rank.apply(
            lambda x: any([x[v] != x[dates[0]] for v in dates[1:]]), axis=1)
        df_out = df_id_rank[df_id_rank["update"]]
        df_title = pd.Series(id2titles_dict).reset_index()
        df_title.columns = [id_col, title_col2]
        df_out = df_out.merge(df_title, on=id_col)[[title_col2] + dates]
        logging.info(f"rank stats = {df_out.shape}")

        parts.append([desc, df_stats, df_out])

    return parts


def update_readme(basedir, moredir, limit=3):
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
    diff_parts = _get_diff_stats(basedir, moredir, MAIN_SITES, desc_list=["豆瓣Top250调整", "IMDb Top250调整"], count_list=[5, 3])
    top_parts = _get_top_stats(basedir, moredir, SITES, desc="电影Top榜单")
    toc = ["- Table of Contents"]
    texts2 = []
    for parts in [extra_parts, diff_parts, top_parts]:
        texts2.append(hr_line)
        for part in parts:
            desc, *df_list = part
            logging.info(f"add {desc}, list={len(df_list)}")
            if df_list and desc:
                desc = desc.strip()
                desc2 = desc.lower().replace(" ", "-")
                toc.append(f"  - [{desc}](#{desc2})")
                texts2.append(f"## {desc}")
            for df in df_list:
                logging.info(f"  data shape={df.shape}")
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
