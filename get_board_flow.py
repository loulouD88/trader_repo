import requests
import pandas as pd
import datetime
import glob
import os
import subprocess

# ---------- 配置 ----------
data_folder = "data"
os.makedirs(data_folder, exist_ok=True)
top_n = 10
today_str = datetime.datetime.now().strftime("%Y-%m-%d")

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

if not all_boards:
    print("没有获取到数据")
    exit(1)

# ---------- 保存当天 CSV ----------
df = pd.DataFrame(all_boards)
df.rename(columns={
    "f12": "板块代码",
    "f14": "板块名称",
    "f62": "主力净流入"
}, inplace=True)
df["主力净流入"] = df["主力净流入"].astype(float)
df["日期"] = today_str
csv_file = f"{data_folder}/行业主力资金排行_{today_str}.csv"
df.to_csv(csv_file, index=False, encoding="utf-8-sig")

# ---------- 三天累计 ----------
all_files = sorted(glob.glob(f"{data_folder}/行业主力资金排行_*.csv"))[-3:]
dfs = [pd.read_csv(f) for f in all_files]
all_data = pd.concat(dfs)
sum_df = all_data.groupby(['板块代码','板块名称'])['主力净流入'].sum().reset_index()
sum_df = sum_df.sort_values(by='主力净流入', ascending=False).head(top_n)
sum_csv_file = f"{data_folder}/三天累计主力净流入_{today_str}.csv"
sum_df.to_csv(sum_csv_file, index=False, encoding="utf-8-sig")

# ---------- 自动 push 到 data 分支（使用 PAT） ----------
try:
    pat = os.environ['GH_PAT']        # workflow Secrets
    username = "loulouD88"
    repo_name = "trader_repo"
    repo_url = f"https://x-access-token:{pat}@github.com/{username}/{repo_name}.git"

    # 设置 git 用户
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)

    # 切换或创建本地 data 分支
    subprocess.run(["git", "fetch"], check=True)
    subprocess.run(["git", "checkout", "-B", "data"], check=True)

    # 只 add 当天文件
    subprocess.run(["git", "add", csv_file, sum_csv_file], check=True)
    subprocess.run(["git", "commit", "-m", f"更新 {today_str} 数据和图表", "--allow-empty"], check=True)

    # 用 PAT URL push
    subprocess.run(["git", "push", repo_url, "data"], check=True)
    print("已成功 push 到 data 分支")
except Exception as e:
    print(f"自动 push 失败: {e}")
