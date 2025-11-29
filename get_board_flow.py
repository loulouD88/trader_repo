import requests
import pandas as pd
import datetime
import glob
import os
import matplotlib.pyplot as plt
import subprocess

# ---------- 配置 ----------
data_folder = "data"
os.makedirs(data_folder, exist_ok=True)
top_n = 10  # 三天累计显示前 N 板块
today_str = datetime.datetime.now().strftime("%Y-%m-%d")

# ---------- 设置中文字体 ----------
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

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

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data_json = response.json()
    except Exception as e:
        print(f"请求失败: {e}")
        exit(1)

    boards = data_json.get("data", {}).get("diff", [])
    if not boards:
        break

    all_boards.extend(boards)
    total_count = data_json.get("data", {}).get("total", 0)
    if page * page_size >= total_count:
        break
    page += 1

if not all_boards:
    print("当天没有获取到板块数据，脚本结束")
    exit(1)

# ---------- 转成 DataFrame ----------
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
df["日期"] = today_str

# 保存当天 CSV
csv_file = os.path.join(data_folder, f"行业主力资金排行_{today_str}.csv")
df.to_csv(csv_file, index=False, encoding='utf-8-sig')
print(f"当天资金流向已保存: {csv_file}")

# ---------- 三天累计 ----------
all_files = sorted(glob.glob(os.path.join(data_folder, "行业主力资金排行_*.csv")))[-3:]
if not all_files:
    print("没有找到过去三天的数据，无法计算三天累计")
    exit(1)

dfs = []
for f in all_files:
    try:
        temp_df = pd.read_csv(f)
        dfs.append(temp_df)
    except Exception as e:
        print(f"读取文件 {f} 失败: {e}")

all_data = pd.concat(dfs)
sum_df = all_data.groupby(['板块代码','板块名称'])['主力净流入'].sum().reset_index()
sum_df = sum_df.sort_values(by='主力净流入', ascending=False).head(top_n)

# 保存三天累计 CSV
sum_csv_file = os.path.join(data_folder, f"三天累计主力净流入_{today_str}.csv")
sum_df.to_csv(sum_csv_file, index=False, encoding='utf-8-sig')
print(f"三天累计前{top_n}板块已保存: {sum_csv_file}")

# ---------- 可视化 ----------
try:
    plt.figure(figsize=(12,6))
    plt.bar(sum_df['板块名称'], sum_df['主力净流入'], color='skyblue')
    plt.title(f"最近三天累计主力净流入前{top_n}板块 ({today_str})", fontsize=16)
    plt.xlabel("板块名称")
    plt.ylabel("累计主力净流入（万元）")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    chart_file = os.path.join(data_folder, f"三天累计主力净流入图_{today_str}.png")
    plt.savefig(chart_file)
    plt.close()
    print(f"三天累计柱状图已保存: {chart_file}")
except Exception as e:
    print(f"生成图表失败: {e}")

# ---------- 自动 push 回仓库 ----------
try:
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", data_folder], check=True)
    subprocess.run(["git", "commit", "-m", f"更新 {today_str} 数据和图表", "--allow-empty"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)  # 指定 main 分支
    print("已自动 push CSV 和图表回仓库")
except Exception as e:
    print(f"自动 push 失败: {e}")
