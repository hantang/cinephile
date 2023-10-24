import re


def strip_space(text):
    return re.sub(r"\s+", " ", text).strip() if text else text


def strip_url(text):
    return text.strip().lstrip("/").strip()


def strip(s, keep=False, slash=False):
    pattern1 = r'[^\S\r\n]+' if keep else r'\s+'
    s = re.sub(pattern1, ' ', s)  # 去除连续空白
    s = re.sub(r'\n\s+', '\n', s)  # 仅保留一个换行
    s = s.strip()
    if slash:
        return s.strip('/').strip()
    return s


def purify_webarchive(html_page):
    # 清除webarchive中添加的信息
    tag1 = "<!-- End Wayback Rewrite JS Include -->"
    tag2 = "</html>"
    b, e = "BEGIN", "END"
    be_pairs = [[b.upper(), e.upper()], [b.lower(), e.lower()], [b.capitalize(), e.capitalize()]]
    pairs = [
        "<!-- BEGIN WAYBACK TOOLBAR INSERT -->",
        "<!-- begin ads footer -->",
        "<!-- begin BOTTOM_AD -->",
        "<!-- begin comscore beacon -->",
        "<!-- begin injectable INJECTED_BILLBOARD -->",
        "<!-- begin injectable INJECTED_NAVSTRIP -->",
        "<!-- Begin SIS code --> ",
        "<!-- begin SRA -->",
        "<!-- begin TOP_AD -->",
        "<!-- begin TOP_AD -->",
        "<!-- begin TOP_RHS -->",
        "<!-- Begin INLINE20 -->",
        "<!-- Begin INLINE40 -->",
        "<!-- Begin INLINEBOTTOM -->",
    ]
    pairs2 = []  # 组成BEGIN ... END
    for pair in pairs:
        for bw, ew in be_pairs:
            pair = pair.replace(bw + " ", ew + " ")
        pairs2.append(pair)

    data = html_page
    i1 = data.find(tag1)
    i2 = data.rfind(tag2)
    data2 = "<html>\n<head>\n" + data[i1 + len(tag1): i2 + len(tag2)].strip()
    for t1, t2 in zip(pairs, pairs2):
        i3a = data2.find(t1)
        i3b = data2.find(t2)
        if i3a == -1 or i3a > i3b:
            continue
        assert i3a < i3b, (i3a, i3b, t1, t2)
        data2 = data2[:i3a] + data2[i3b + len(t2):]

    pattern = r"(https?://web.archive.org)?/web/(20|19)\d+\w+/http"
    data3 = re.sub(pattern, "http", data2)
    return data3
