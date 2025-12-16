import requests
import pandas as pd
import datetime
import glob
import os
import subprocess
import sys

# ========== 基础配置 ==========
DATA_DIR = "data"
TOP_N = 10
TODAY = datetime.datetime.now().strftime("%Y-%m-%d")

os.makedirs(DATA_DIR, exist_ok=True)

# ========== 拉取资金流 ==========
url = "https://push2.eastmoney.com/api/qt/clist/get"
all_boards = []
page = 1
page_size = 50

while True:
    params = {
        "pn": page,
        "pz": page_size,
        "po": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fid": "f62",
        "fs": "m:90 t:2",
        "fields": "f12,f14,f62"
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    j = r.json()
    diff = j.get("data", {}).get("diff", [])
    if not diff:
        break
    all_boards.extend(diff)
    total = j.get("data", {}).get("total", 0)
    if page * page_size >= total:
        break
    page += 1

if not all_boards:
    print("❌ 没有获取到任何数据")
    sys.exit(1)

df = pd.DataFrame(all_boards)
df.rename(columns={
    "f12": "板块代码",
    "f14": "板块名称",
    "f62": "主力净流入"
}, inplace=True)

df["主力净流入"] = df["主力净流入"].astype(float)
df["日期"] = TODAY

daily_csv = f"{DATA_DIR}/行业主力资金排行_{TODAY}.csv"
df.to_csv(daily_csv, index=False, encoding="utf-8-sig")

# ========== 三日累计 ==========
files = sorted(glob.glob(f"{DATA_DIR}/行业主力资金排行_*.csv"))[-3:]
dfs = [pd.read_csv(f) for f in files]
sum_df = (
    pd.concat(dfs)
    .groupby(["板块代码", "板块名称"], as_index=False)["主力净流入"]
    .sum()
    .sort_values("主力净流入", ascending=False)
    .head(TOP_N)
)

sum_csv = f"{DATA_DIR}/三天累计主力净流入_{TODAY}.csv"
sum_df.to_csv(sum_csv, index=False, encoding="utf-8-sig")

# ========== Git 自动提交 ==========
pat = os.environ.get("GH_PAT")
if not pat:
    print("❌ 未找到 GH_PAT")
    sys.exit(1)

USERNAME = "loulouD88"
REPO = "trader_repo"
REMOTE = f"https://x-access-token:{pat}@github.com/{USERNAME}/{REPO}.git"

def run(cmd):
    subprocess.run(cmd, check=True)

run(["git", "config", "--global", "user.name", "github-actions"])
run(["git", "config", "--global", "user.email", "actions@github.com"])

run(["git", "fetch", "origin"])
run(["git", "checkout", "-B", "data", "origin/data"])

# ⭐ 关键：先 rebase 再提交
run(["git", "pull", "--rebase", "origin", "data"])

run(["git", "add", daily_csv, sum_csv])
run(["git", "commit", "-m", f"更新 {TODAY} 行业资金数据", "--allow-empty"])
run(["git", "push", REMOTE, "data"])

print("✅ 数据已成功推送到 data 分支")
