import pandas as pd


def save_data(file="StartingList.xlsx", max_year=2024, is_21st=False):
    def _adjust(text):
        # 调整导演姓名顺序
        text = str(text).strip()
        tlist = [t.strip() for t in text.split("&")]
        return " & ".join([" ".join([v.strip() for v in tlist[0].strip().split(",")[::-1]])] + tlist[1:])

    cols_base = ['idTSPDT', 'Title', 'Director(s)', 'Year', 'Country', 'Length', 'Genre', 'Colour']
    cols_update = ['Director(s)']
    cols_name = [
        'TSPDT-ID', 'Title 电影', 'Director 导演', 'Year 年份', 'Region 地区', 'Genre 类型', 'Length 片长', 'Colour 色彩'
    ]
    col_id = cols_base[0]

    if is_21st:
        savefile = f"./tspdt-top1000-years-21stcentury-2008T{max_year}.csv"
        cols_date = [f'Y{d}' for d in range(max_year, 2007, -1)]
    else:
        savefile = f"./tspdt-top1000-years-2006T{max_year}.csv"
        cols_date = [f'Y{d}' for d in range(max_year, 2006, -1) if d not in [2009]] + ['Y2006-Dec', 'Y2006-Mar']
    cols_out = ["Index"] + cols_name + cols_date

    dfe = pd.read_excel(file)
    cols_date_raw = dfe.columns[8:-2]
    assert len(cols_date_raw) == len(cols_date)
    dfe2 = dfe.rename(columns=dict(zip(cols_date_raw, cols_date)))[cols_base + cols_date]
    dfe2[cols_date] = dfe2[cols_date].replace("---", 0).fillna(0).astype("int")

    ids = []
    for d in cols_date:
        ids.append(dfe2[dfe2[d].between(1, 1000)][col_id])
    ids_all = pd.concat(ids).drop_duplicates()

    dfe2a = dfe2[dfe2[col_id].isin(ids_all)].copy()
    dfe2b = dfe2a.sort_values(cols_date)
    dfe2c = dfe2b.reset_index(drop=True).reset_index()
    for col in cols_update:
        dfe2c[col] = dfe2c[col].apply(_adjust)
    dfe2c.columns = cols_out

    dfe2c[cols_date] = dfe2c[cols_date].replace(0, "---")
    dfe2c.to_csv(savefile, index=False)

# save_data(file='StartingList.xlsx', is_21st=False)
# save_data(file='StartingList_21stCentury.xlsx', is_21st=True)
