import json
import logging
from pathlib import Path
from typing import List, Union

from cinephile.crawlers.base import BaseCrawler, CrawlerUrl
from cinephile.utils import datetimes
from cinephile.utils.texts import purify_webarchive

"""
网页查询
https://web.archive.org/web/20230000000000*/{url}

JSON接口:

- 查询一段时间 【推荐】
`http://web.archive.org/cdx/search/cdx`
https://web.archive.org/cdx/search/cdx?url={url}&from=20000101&to=20231020&output=json

- 查询1年
https://web.archive.org/__wb/calendarcaptures/2?url={url}&date=2011&groupby=day
返回日期
{"items":[[1224,301,1]]}

- 查询1天
https://web.archive.org/__wb/calendarcaptures/2?url={url}&date=20111224
返回时间戳
{"colls":[["51_crawl","alexa_2007","alexacrawls"]],"items":[[84712,200,0]]}
"""


class WebArchiveUrl(CrawlerUrl):
    def __init__(self, sitename, description=None, baseurl=None):
        self._key_page_snapshot = f"{sitename}-page-snapshot"
        self._key_api_timestamps = f"{sitename}-api-timestamps"
        self._key_api_snapshots = f"{sitename}-api-snapshots"
        self.baseurl = baseurl
        super().__init__(sitename, description)

    @property
    def key_page_snapshot(self):
        return self._key_page_snapshot

    @property
    def key_api_timestamps(self):
        return self._key_api_timestamps

    @property
    def key_api_snapshots(self):
        return self._key_api_snapshots

    def url(self, key: str, **kwargs) -> str:
        config = self.url_dict[key]
        base_url = config["url"]
        if key == self._key_api_timestamps:
            target_url = kwargs["target_url"]
            query_date = kwargs["query_date"]
            params = config["params2"].format(target_url, query_date)
            return f"{base_url}?{params}"
        if key == self._key_api_snapshots:
            target_url = kwargs["target_url"]
            start_date = kwargs["start_date"]
            end_date = kwargs["end_date"]
            params = config["params"].format(target_url, start_date, end_date)
            return f"{base_url}?{params}"

    def source(self, key: str, **kwargs) -> Union[str, List[str]]:
        return self.baseurl

    def _init_urls(self):
        return {
            self._key_page_snapshot: {
                "url": "http://web.archive.org/web/{}/{}",  # timestamp/url
                "desc": "快照页面",
                "status": 200,
            },
            self._key_api_snapshots: {
                "url": "http://web.archive.org/cdx/search/cdx",
                "params": "url={}&from={}&to={}&output=json",
                "desc": "查询一段时间内快照地址",
            },
            self._key_api_timestamps: {
                "url": "https://web.archive.org/__wb/calendarcaptures/2",
                # "params1": "url={}&date={}&groupby=day",
                "params2": "url={}&date={}",
                "desc": "按天或年聚合查询快照时间戳",
            },
        }


class WebArchiveCrawler(BaseCrawler):
    def __init__(self, savedir=None, overwrite=False, **kwargs):
        super().__init__(savedir, overwrite, **kwargs)
        self.sitename = "webarchive"
        self.baseurl = "https://web.archive.org/"
        self.description = "web.archive快照查询和下载"
        self.urls = WebArchiveUrl(self.sitename, self.description, self.baseurl)

    def parse_page(self, key, page, char_detect=False, **kwargs):
        pass

    def process(self, key=None, savedir=None, **kwargs):
        pass

    def getname(self, dt=None, name=None, post=None, suffix="json"):
        # webarchive-query-xxx-v20230101.json
        dt2 = datetimes.time2str(dt if dt else self.dt, 3)
        category = name if name else ""
        post = "" if not post else post
        parts = [self.sitename, "query", category, post, "v" + dt2]
        parts = "-".join([v for v in parts if len(v) > 0])
        savename = f"{parts}.{suffix}"
        return savename

    def save(self, savefile, data, **kwargs):
        filename = Path(savefile)
        if not filename.parent.exists():
            logging.info(f"create dir = {filename.parent}")
            filename.parent.mkdir(parents=True)
        logging.info(f"save to {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("save done\n\n")

    def query_timestamps(self, target_url, query_date, savedir=None):
        # 根据日期查询时间戳
        key = self.urls.key_api_timestamps
        dt = datetimes.utcnow()

        url_config = self.urls.query(key)
        savename = self.getname(dt, name="timestamps")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, savefile

        query_date = str(query_date)[:8]
        assert query_date.isdigit() and len(query_date) in [4, 6, 8]
        logging.info("query_date = {query_date}")
        headers = self.get_headers()
        api_url = self.get_url(key, target_url=target_url, query_date=query_date)
        result = self.get_page(api_url, headers, page_format="json")
        if not result:
            logging.warning(f"Error get {api_url}")
            return self.error_http, savefile
        logging.info(f"result = {len(result)} " + str(type(result)))
        data = {
            "sitename": self.sitename,
            "update_time": datetimes.time2str(dt, 1),
            "description": url_config["desc"],
            "target_url": target_url,
            "query_date": query_date,
            "result": result,
        }
        self.save(savefile, data)
        return 1, savefile

    def query_snapshots(self, target_url, dates=None, savedir=None):
        """查询target_url在时间范围的所有web.archive快照地址，返回json数据"""
        key = self.urls.key_api_snapshots
        dt = datetimes.utcnow()
        url_config = self.urls.query(key)
        savename = self.getname(dt, name=f"snapshots")
        savefile = Path(savedir if savedir else self.savedir, savename)
        if self.check(savefile) and not self.overwrite:
            return self.error_file_exist, savefile

        headers = self.get_headers()
        # 设置时间范围，可以根据需要进行调整
        if dates:
            start_date, end_date = dates
        else:
            start_date, end_date = "20000101", datetimes.time2str(self.dt, 4)
        start_date = start_date.replace("-", "")
        end_date = end_date.replace("-", "")
        assert len(start_date) == 8 and len(end_date) == 8
        api_url = self.get_url(key, target_url=target_url, start_date=start_date, end_date=end_date)
        result = self.get_page(api_url, headers, page_format="json")
        if not result:
            logging.warning(f"Error get {api_url}")
            return self.error_http, savefile
        logging.info(f"result = {len(result)} " + str(type(result)))
        data = {
            "sitename": self.sitename,
            "update_time": datetimes.time2str(dt, 1),
            "description": url_config["desc"],
            "target_url": target_url,
            "start_date": start_date,
            "end_date": end_date,
            "result": result,
        }
        self.save(savefile, data)
        return 1, savefile

    def save_snapshots(self, snapshots, output_dir, prefix=None, overwrite=False, purify=True):
        key = self.urls.key_page_snapshot
        url_config = self.urls.query(key)
        base_url = url_config["url"]
        status = url_config.get("status", 200)

        output_dir = Path(output_dir)
        if not output_dir.exists():
            logging.info(f"mkdir output dir = {output_dir}")
            output_dir.mkdir(parents=True)

        logging.info(f"snapshots = {len(snapshots)}")
        headers = self.get_headers()
        rn = len(snapshots)
        total_cnt, success, fail = 0, 0, 0
        for ri, snapshot in enumerate(snapshots):
            _, timestamp, archived_url, mimetype, statuscode, _, _ = snapshot
            if statuscode is None or not statuscode.isdigit() or int(statuscode) != status:  # keep 200 pages
                logging.info(f"round={ri + 1}/{rn}, ignore: {snapshot}")
                continue

            total_cnt += 1
            name = f"{prefix}-{timestamp}" if prefix else timestamp
            filename = Path(output_dir, f"{name}.html")
            filename2 = Path(output_dir, f"{name}-purify.html")
            if filename.exists() and not overwrite:
                continue

            snapshot_url = base_url.format(timestamp, archived_url)
            html_content = self.get_page(snapshot_url, headers, round_i=ri + 1, round_n=rn)
            if html_content:
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(html_content)

                if purify:
                    html_content2 = purify_webarchive(html_content)
                    with open(filename2, "w", encoding="utf-8") as file:
                        file.write(html_content2)
                logging.info(f"save to：{filename}")
                success += 1
            else:
                fail += 1
        logging.info(f"stats: all={rn}, total={total_cnt}, success={success}, fail={fail}")


if __name__ == "__main__":
    # example
    save_dir = "./temp-data"
    output_dir = "./temp-html"
    target_url = "https://movie.douban.com"
    crawler = WebArchiveCrawler(save_dir)

    # crawler.query_timestamps(target_url, query_date="20220102", savedir=None)
    # crawler.query_timestamps(target_url, query_date="202201", savedir=None)
    status, file = crawler.query_snapshots(target_url, dates=("20230101", "20230301"), savedir=None)
    with open(file) as f:
        data = json.load(f)
    snapshots = data["result"][:3]
    prefix = "douban-movie"
    crawler.save_snapshots(snapshots, output_dir, prefix=prefix, overwrite=False)
