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

更新器預設使用 `data/tv_live.json` 作為增量基準：從最新搜尋頁開始掃描，遇到既有公告便停止，下載所有新回次，並固定重新下載最新 2 回（包含尚未播出的回次），讓公告後續修改可以同步。更舊的公告不會重新請求。只有回數連續、日期有效且每回皆有名單時，才會替換 `data/tv_live.json` 與瀏覽器使用的 `web/data.js`。

第一次建立資料，或修改了會影響舊回次的解析規則與 `corrections.json` 時，可手動完整重建：

```powershell
python update_data.py --full
```

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
4. 將更新後的 `data/tv_live.json` 提交回 `main`，作為下次增量更新的基準。
5. 上傳 `web/` 作為 Pages artifact。
6. 使用 `actions/deploy-pages` 部署到 GitHub Pages。

第一次使用前，請到 GitHub repository 的 Settings → Pages，將 Build and deployment 的 Source 設為 GitHub Actions；並在 Settings → Actions → General → Workflow permissions 選擇 **Read and write permissions**，讓 workflow 可以保存增量資料。若 `main` 有 branch protection，也需允許 GitHub Actions 寫入，否則部署當次雖能產生資料，下一次執行卻無法沿用。

資料來源為 [BanG Dream! 官方網站](https://bang-dream.com/news/)。本專案為非官方統計工具。
