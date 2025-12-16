import requests
import pandas as pd
import datetime
import glob
import os
import subprocess

# ---------- 基础配置 ----------
data_folder = "data"
os.makedirs(data_folder, exist_ok=True)

top_n = 10
today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")

# ---------- 获取数据 ----------
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
        "fields": "f12,f14,f62"
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", {})
    diff = data.get("diff", [])

    if not diff:
        break

    all_boards.extend(diff)
    total = data.get("total", 0)
    if page * page_size >= total:
        break
    page += 1

if not all_boards:
    raise RuntimeError("未获取到任何板块数据")

# ---------- 保存当天 ----------
df = pd.DataFrame(all_boards)
df.rename(columns={
    "f12": "板块代码",
    "f14": "板块名称",
    "f62": "主力净流入"
}, inplace=True)

df["主力净流入"] = df["主力净流入"].astype(float)
df["日期"] = today_str

csv_today = f"{data_folder}/行业主力资金排行_{today_str}.csv"
df.to_csv(csv_today, index=False, encoding="utf-8-sig")

# ---------- 三天累计 ----------
files = sorted(glob.glob(f"{data_folder}/行业主力资金排行_*.csv"))[-3:]
dfs = [pd.read_csv(f) for f in files]

sum_df = (
    pd.concat(dfs)
    .groupby(["板块代码", "板块名称"], as_index=False)["主力净流入"]
    .sum()
    .sort_values("主力净流入", ascending=False)
    .head(top_n)
)

csv_3day = f"{data_folder}/三天累计主力净流入_{today_str}.csv"
sum_df.to_csv(csv_3day, index=False, encoding="utf-8-sig")

# ---------- Git Push（关键修复点） ----------
pat = os.environ["GH_PAT"]
username = "loulouD88"
repo = "trader_repo"
repo_url = f"https://x-access-token:{pat}@github.com/{username}/{repo}.git"

def run(cmd):
    subprocess.run(cmd, check=True)

run(["git", "config", "--global", "user.name", "github-actions"])
run(["git", "config", "--global", "user.email", "actions@github.com"])

# 拉取远程
run(["git", "fetch", repo_url])

# 切换 / 创建 data 分支
run(["git", "checkout", "-B", "data"])

# ⭐ 关键：rebase 远程 data，避免 non-fast-forward
run(["git", "rebase", f"{repo_url}/data"])

# 提交
run(["git", "add", csv_today, csv_3day])
run(["git", "commit", "-m", f"更新 {today_str} 行业资金数据", "--allow-empty"])

# 推送
run(["git", "push", repo_url, "data"])
