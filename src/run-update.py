import argparse
import json
import logging
from pathlib import Path

import pandas as pd
from deprecated import deprecated

from cinephile.utils import datetimes
from cinephile.utils.misc import set_logging
from cinephile.utils.movies import MovieCluster


BASEDIR = ".."
MISCDIR = "misc"
SITES = ["douban", "imdb", "mtime", "maoyan", "tmdb"]
MAIN_SITES = ["douban", "imdb"]
EXTRA_SITES = ["douban-weekly"]
SITE_DESC = [
    "豆瓣电影 Top250",
    "IMDb电影 Top250",
    "时光电影 Top100",
    "猫眼电影 Top100",
    "TMDB 高分电影"
]
FRONT_MATTER = """
---
hide:
  - toc
---
"""


def _get_top_stats(datadir, moredir, names, desc="", merge=True):
    # douban, imdb ... top250/top100 movies show as table
    file_dict = {}
    for site in names:
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
            file_dict[site] = file
        else:
            logging.warning(f"Empty file in {site}: datadir={datadir}")
    if len(file_dict) == 0:
        logging.warning("files are empty")
        return []

    data_dict = {}
    urls = []
    for site in names:
        if site not in file_dict: continue
        file = file_dict[site]
        logging.info(f"read file = {file}")
        with open(file) as f:
            data = json.load(f)
        data_dict[site] = data
        url_hits = [v in file.name for v in MAIN_SITES]
        urls.append(True if any(url_hits) else False)
    if merge:
        data_list = [data_dict[site] for site in names if site in data_dict]
        mc = MovieCluster.merge_from_json(*data_list)
        df = mc.to_df_table(keep_url=urls, keep_cover=False, merge_clusters=True)
        part = [[desc, df]]
        return part
    else:
        df_csv_dict = {}
        for site, data in data_dict.items():
            mc = MovieCluster.from_json(data)
            csv = mc.to_df_csv(keep_url=True, keep_cover=True)
            source_link = mc.source
            if isinstance(source_link, list):
                source_link = source_link[0]
            df_csv_dict[site] = [csv, mc.release_time, source_link]
        return df_csv_dict


def _get_extra_stats(datadir, names):
    files = []
    for site in names:
        tmpdir = Path(datadir, site)
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
        df = mc.to_df_table(keep_url=True, keep_cover=True, split_cover=True, merge_clusters=True)
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
            dfx2 = dfx[[id_col, rank_col]].copy().astype(str)
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
        df_id_rank[dates] = df_id_rank[dates]
        df_id_rank["update"] = df_id_rank.apply(
            lambda x: any([str(x[v]) != str(x[dates[0]]) for v in dates[1:]]), axis=1)
        df_out = df_id_rank[df_id_rank["update"]]
        df_title = pd.Series(id2titles_dict).reset_index()
        df_title.columns = [id_col, title_col2]
        df_out = df_out.merge(df_title, on=id_col)[[title_col2] + dates]
        df_out[dates] = df_out[dates].fillna(999).astype(int)
        df_out = df_out.sort_values(dates[::-1]).reset_index(drop=True)
        df_out[dates] = df_out[dates].astype("str")
        for dt in dates:
            df_out[dt] = df_out[dt].replace("999", "-").astype("str")
        logging.info(f"rank stats = {df_out.shape}")

        parts.append([desc, df_stats, df_out])

    return parts


@deprecated(reason="no more update readme.md")
def update_readme(basedir, moredir, limit=50):
    readfile = Path(f"{BASEDIR}/README.md")
    hr_line = "-" * 3
    more_line = "<!-- more -->"
    raw_readmes = []
    update_line = "最近更新："
    update_line_num = -1
    if readfile.exists():
        with open(readfile) as f:
            line_num = 0
            for line in f:
                line_num += 1
                line = line.rstrip()
                raw_readmes.append(line)
                if line == more_line or line_num > limit:
                    break
                if line.startswith(update_line) and update_line_num < 0:
                    update_line_num = line_num - 1

    logging.info(f"readme = \n" + '\n'.join(raw_readmes))
    update_line2 = update_line + str(datetimes.time2zh())
    if update_line_num >= 0:
        raw_readmes[update_line_num] = update_line2
    else:
        raw_readmes.append(update_line2)
    texts = [
        "\n".join(raw_readmes).strip(),
    ]

    extra_parts = _get_extra_stats(basedir, EXTRA_SITES)
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


def update_docs(basedir, moredir):
    dt = str(datetimes.time2zh())
    extra_parts = _get_extra_stats(basedir, EXTRA_SITES)
    diff_parts = _get_diff_stats(basedir, moredir, MAIN_SITES, desc_list=["豆瓣Top250调整", "IMDb Top250调整"], count_list=[5, 3])
    top_parts = _get_top_stats(basedir, moredir, SITES, desc="电影Top榜单")
    top_csv_dict = _get_top_stats(basedir, moredir, SITES, merge=False)

    docdir = Path(f"{BASEDIR}/docs/top250")
    if not docdir.exists():
        docdir.mkdir(parents=True)

    for name, parts in zip(["douban-weekly.md", "index.md"], [extra_parts, top_parts]):
        part_texts = []
        for part in parts:
            desc, *df_list = part
            if df_list and desc:
                if len(part_texts) <= 1:
                    part_texts.append(f"# {desc}")
                    part_texts.append(f"> 更新于：{dt}")
                else:
                    part_texts.append(f"## {desc}")

            for df in df_list:
                logging.info(f"  data shape={df.shape}")
                part_texts.append(df.to_markdown())
        
        savefile = Path(docdir, name)
        # if savefile.name == "index.md":
        part_texts = [FRONT_MATTER.strip()] + part_texts
        with open(savefile, "w") as f:
            f.write("\n\n".join(part_texts).strip() + "\n")

    # top_parts
    more_texts = []
    more_toc = ["- **目录**"]
    for site, (df_csv, release_time, source_link) in top_csv_dict.items():
        csvfile = Path(basedir, "csv2", f"{site}.csv")
        if not csvfile.parent.exists():
            csvfile.parent.mkdir(parents=True)
        df_csv.to_csv(csvfile, index=True)
        csvfile_path = f"../../data/{csvfile.parent.name}/{csvfile.name}"

        if site not in MAIN_SITES:
            desc = SITE_DESC[SITES.index(site)].strip()
            desc2 = desc.lower().replace(" ", "-")
            more_toc.append(f"  - [{desc}](#{desc2})")
            if len(more_texts) > 0:
                more_texts.append("---")
            more_texts.extend([
                "## {}".format(desc),
                f"> 数据更新于：{release_time}\n> \n> 来源: [链接]({source_link})",
                f'{{{{ read_csv("{csvfile_path}") }}}}',
            ])
        else:
            main_texts = []
            main_toc = ["- **目录**"]
            part = diff_parts[MAIN_SITES.index(site)]
            diff_desc, *df_list = part
            desc_list = [diff_desc, "评分统计","排名调整"]
            for i in range(len(desc_list)):
                desc = desc_list[i]
                indent = 2 if i == 0 else 3
                hashtag = "#" * indent
                spaces = " " * 2 * (indent-1)
                if desc:
                    desc2 = desc.lower().replace(" ", "-")
                    main_texts.append(f"{hashtag} {desc}")
                    main_toc.append(f"{spaces}- [{desc}](#{desc2})")
                if i > 0:
                    df = df_list[i-1]
                    logging.info(f"  data shape={df.shape}")
                    main_texts.append(df.to_markdown())

            desc = "完整榜单"
            desc2 = desc.lower().replace(" ", "-")
            main_toc.append(f"  - [{desc}](#{desc2})")
            main_texts.extend([
                "---",
                f"## {desc}",
                f'{{{{ read_csv("{csvfile_path}") }}}}'
            ])
            main_texts = [
                "# {}".format(SITE_DESC[SITES.index(site)]),
                f"> 数据更新于：{release_time}\n> \n> 来源: [链接]({source_link})",
                "\n".join(main_toc),
                 "---"
            ] + main_texts
            savefile = Path(docdir, f"{site}.md")
            with open(savefile, "w") as f:
                f.write("\n\n".join(main_texts).strip() + "\n")

    if more_texts:
        more_texts =  [
            "# 更多高分电影榜单",
            f"> 更新于：{dt}",
            "\n".join(more_toc),
            "---"
        ] + more_texts
        savefile = Path(docdir, "more.md")
        with open(savefile, "w") as f:
            f.write("\n\n".join(more_texts).strip() + "\n")


if __name__ == "__main__":
    set_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--datadir", type=str, help="data dir", default=f"{BASEDIR}/data")
    args = parser.parse_args()
    logging.info(f"args = {args}\n")
    # update_readme(args.datadir, moredir=f"{BASEDIR}/archive")
    update_docs(args.datadir, moredir=f"{BASEDIR}/archive")
    logging.info(f"done\n")
