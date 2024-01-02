from cinephile.utils import datetimes


def get_savename(site, total, dt):
    dt2 = datetimes.time2str(dt, 3)
    if int(total) in [0, 1]:
        total = ""
    savename = f"{site}-movie-top{total}-v{dt2}.json".strip("-")
    return savename
