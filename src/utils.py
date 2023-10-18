import datetime
import pytz


def get_table(table, index=True):
    sep = " | "
    min_len = 2
    row_cnt = max([len(col) for col in table])
    header = ["**{}**".format(col[0]) for col in table]
    if index:
        header = ["**排序**"] + header
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


def get_dt():
    def _num2str(n, num):
        if 0 <= n <= 10:
            return num[n]
        elif n <= 99:
            return (num[n // 10] + num[-1] + num[n % 10]).lstrip(num[1]).rstrip(num[0])
        return n

    num = "〇一二三四五六七八九十"
    dt = datetime.datetime.now(tz=pytz.timezone("Asia/Shanghai"))
    year = "".join([num[int(i)] for i in str(dt.year)])
    month = _num2str(dt.month, num)
    day = _num2str(dt.day, num)
    week = num[dt.isoweekday()]
    extra = dt.strftime("%H:%M:%S %z(%Z)")

    return f"{year}年{month}月{day}日（星期{week}）{extra}"
