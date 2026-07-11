# BanG Dream! TV LIVE 出演統計

本機互動式儀表板，整理現行 `BanG Dream! TV LIVE 2020–` 系列自第 1 回起的官方出演公告，並計算每位聲優最近一次出場。

## 第一次使用

在此資料夾開啟 PowerShell：

```powershell
python -m pip install -r requirements.txt
python update_data.py
start .\web\index.html
```

`web/index.html` 會讀取同資料夾的 `data.js`，因此可直接開啟，不需要啟動伺服器。

## 更新資料

```powershell
python update_data.py
```

更新器會先擷取、解析並驗證完整資料；只有回數連續、日期有效且每回皆有名單時，才會替換 `data/tv_live.json` 與瀏覽器使用的 `web/data.js`。人工修正集中在 `corrections.json`，不會混入解析程式。

## 統計規則

- 一般出演、MC、嘉賓、遠端出演與 VTR 都會更新「上次出場」。
- 官方公告記載取消、欠席或出演見送り者不計入出場次數。
- 尚未播出的公告只出現在「預定出演」，不影響歷史排行。
- 含有「角色名 役」的出演者預設歸類為聲優；VTuber 也透過 `corrections.json` 歸入聲優範圍，其他人員可在儀表板切換查看。

## 測試

```powershell
python -m unittest discover -s tests -v
node .\tests\dashboard.test.js
```

## GitHub Pages 自動部署

已提供 `.github/workflows/deploy-pages.yml`。推到 `main`、手動執行 workflow，或每天 UTC 19:00 會自動：

1. 安裝 Python 依賴。
2. 執行 `python update_data.py` 抓取最新官方公告。
3. 執行 Python 與前端檢查。
4. 上傳 `web/` 作為 Pages artifact。
5. 使用 `actions/deploy-pages` 部署到 GitHub Pages。

第一次使用前，請到 GitHub repository 的 Settings → Pages，將 Build and deployment 的 Source 設為 GitHub Actions。

資料來源為 [BanG Dream! 官方網站](https://bang-dream.com/news/)。本專案為非官方統計工具。
