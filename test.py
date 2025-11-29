import requests
import pandas as pd
import datetime
import glob
import os
import matplotlib.pyplot as plt

# ---------- 配置 ----------
data_folder = "data"
os.makedirs(data_folder, exist_ok=True)
top_n = 10  # 三天累计显示前 N 板块

# ---------- 获取当天资金流向 ----------
url = "https://push2.eastmoney.com/api/qt/clist/get"
all_boards = []
page = 1
page_size = 50

while True:
    params = {
        "pn": str(page),
        "pz": str(page_size),
        "po": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fid": "f62",
        "fs": "m:90 t:2",
        "fields": "f12,f14,f62,f66,f69,f72,f75"
    }

    response = requests.get(url, params=params)
    data_json = response.json()
    boards = data_json.get("data", {}).get("diff", [])

    if not boards:
        break

    all_boards.extend(boards)

    total_count = data_json.get("data", {}).get("total", 0)
    if page * page_size >= total_count:
        break

    page += 1

df = pd.DataFrame(all_boards)
df.rename(columns={
    "f12": "板块代码",
    "f14": "板块名称",
    "f62": "主力净流入",
    "f66": "超大单",
    "f69": "大单",
    "f72": "中单",
    "f75": "小单"
}, inplace=True)

numeric_cols = ["主力净流入", "超大单", "大单", "中单", "小单"]
df[numeric_cols] = df[numeric_cols].astype(float)
today_str = datetime.datetime.now().strftime("%Y-%m-%d")
df["日期"] = today_str

csv_file = os.path.join(data_folder, f"行业主力资金排行_{today_str}.csv")
df.to_csv(csv_file, index=False, encoding='utf-8-sig')
print(f"当天资金流向已保存: {csv_file}")

# ---------- 三天累计 ----------
all_files = sorted(glob.glob(os.path.join(data_folder, "行业主力资金排行_*.csv")))[-3:]
dfs = [pd.read_csv(f) for f in all_files]
all_data = pd.concat(dfs)

# 按板块累加三天主力净流入
sum_df = all_data.groupby(['板块代码','板块名称'])['主力净流入'].sum().reset_index()
sum_df = sum_df.sort_values(by='主力净流入', ascending=False).head(top_n)

print("最近三天累计主力净流入前十板块：")
print(sum_df)

# ---------- 可视化 ----------
plt.figure(figsize=(12,6))
plt.bar(sum_df['板块名称'], sum_df['主力净流入'], color='skyblue')
plt.title(f"最近三天累计主力净流入前{top_n}板块 ({today_str})", fontsize=16)
plt.xlabel("板块名称")
plt.ylabel("累计主力净流入（万元）")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()
