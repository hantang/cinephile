import pendulum


def now() -> pendulum.DateTime:
    return pendulum.now()


def utcnow() -> pendulum.DateTime:
    return pendulum.now("UTC")


def bjnow() -> pendulum.DateTime:
    # 北京时间
    return pendulum.now(tz="Asia/Shanghai")


def tsnow() -> int:
    # timestamp
    return int(pendulum.now().timestamp() * 1000)


def time2str(ti, fmt=0) -> str:
    formats = {
        0: "YYYY-MM-DD HH:mm:ss",
        1: "YYYY-MM-DDTHH:mm:ssZZ",
        2: "YYYY-MM-DD",
        3: "YYYYMMDD",
    }
    if not ti:
        ti = pendulum.now()
    return ti.format(formats[fmt])


def time2zh(ti=None) -> str:
    # 中文格式日期时间： 二〇二三年十月二十二日（星期日）17:09:04 +0800
    num = "〇一二三四五六七八九十"

    def _num2str(n):
        if 0 <= n <= 10:
            return num[n]
        elif n <= 99:
            return (num[n // 10] + num[-1] + num[n % 10]).lstrip(num[1]).rstrip(num[0])
        return n

    dt = ti if ti else bjnow()
    year = "".join([num[int(i)] for i in str(dt.year)])
    month = _num2str(dt.month)
    day = _num2str(dt.day)
    week = num[dt.isoweekday()] if dt.isoweekday() < 7 else '日'
    extra = dt.strftime("%H:%M:%S %z")

    return f"{year}年{month}月{day}日（星期{week}）{extra}"


def timestamp2str(ts, fmt=2) -> str:
    if ts is None:
        ti = pendulum.now()
    ti = pendulum.from_timestamp(ts)
    return time2str(ti, fmt)
