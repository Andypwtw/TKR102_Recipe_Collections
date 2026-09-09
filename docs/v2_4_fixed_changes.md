# v2.4 FIXED 修正摘要

本版統一 Docker、VS Code、uv 與 Python 路徑，避免 `.venv`、`/opt/venv`、`PYTHONPATH` 與 `/workspace` 混用。

## 固定開發環境

- Python container：`recipe-python`
- Workspace：`/workspace`
- Python 專案：`/workspace/python`
- uv 虛擬環境：`/opt/venv`
- Python interpreter：`/opt/venv/bin/python`
- Docker 內 MySQL：`mysql:3306`
- Mac Workbench：`127.0.0.1:3307`

## 已修正

1. `docker-compose.yml`：Python 對 MySQL 改用 Compose service name `mysql`。
2. `.vscode/settings.json`：固定 interpreter 為 `/opt/venv/bin/python`，不再指向專案 `.venv`。
3. 新增 `.devcontainer/devcontainer.json`：可直接用 `Dev Containers: Reopen in Container`。
4. 新增 `.vscode/tasks.json` 與 `.vscode/launch.json`。
5. 新增 `scripts/00_check_environment.py` 作為環境檢查。
6. 所有 ETL script 的資料路徑改為由檔案位置計算 `PROJECT_ROOT`，不再寫死 `/workspace/data/...`。
7. 所有需要 `app` 的 script 會自行將 `python/` 加入 `sys.path`，避免 `ModuleNotFoundError: app`。
8. `10_pipeline.py` 會主動設定 `PYTHONPATH`、`cwd`，並用目前 interpreter 執行子程式。
9. Pipeline 補回 `03a_build_unit_weight_map.py`，並放在正規化前執行。
10. `recommendation.py` 的 alias JSON 路徑改為專案相對路徑。

## 驗證結果

已在建立環境中完成：

- Python compileall：成功
- `00_check_environment.py`：成功
- `01_profile_raw_json.py`：成功
- `02_clean_recipes.py`：29,597 筆食譜成功
- `03a_build_unit_weight_map.py`：49 組候選、45 組 ACTIVE、4 組 REVIEW
- `03_normalize_recipes.py`：257,537 筆材料，其中 140,364 筆取得 `weight_g`

Docker daemon 不存在於產檔環境，因此無法在此實際啟動 Compose；Docker/VS Code 設定已做靜態一致性修正。
