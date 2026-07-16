# SOP Tool 練習環境 — 設定說明（靜態前端 + 雲端資料庫版）

架構：**前端是純靜態網頁**（HTML/CSS/JS），你可以放在 GitHub Pages 或任何其他 http(s) 空間；**資料庫在雲端**（Google Sheet），透過 Apps Script 開放一組 API 給前端讀寫。

> ⚠️ 前端一定要透過 `http://` 或 `https://` 網址打開（例如 GitHub Pages 網址），**不能用雙擊本機檔案（`file://`）打開**——瀏覽器會把本機檔案的來源標記成 `null`，Google Apps Script 對這種來源的請求常常會被 CORS 擋掉，這是瀏覽器安全機制，不是程式碼問題。GitHub Pages 天生就是 `https://`，所以這個問題不存在。

## 檔案總覽
| 檔案 | 用途 |
|---|---|
| `list.html` | 案件清單，起始頁 |
| `detail.html` | 練習畫面（讀 `?id=案件編號`），含互動式 SOP 決策樹 |
| `edit.html` | 新增／編輯單筆案件表單 |
| `import.html` | 批次匯入多筆案件（貼上/上傳 JSON 陣列） |
| `sop-editor.html` | 設定全案件共用的 SOP 決策樹流程（產生 `sop_flow.json`） |
| `sop_flow.json` | SOP 流程的實際資料，靜態檔案，放跟其他頁面同一層 |
| `merge_sop_flows.py` | 本機執行的 Python 腳本，把多個正式環境匯出的 SOP flow JSON 合併成一份 `sop_flow.json` |
| `style.css` | 共用樣式 |
| `config.js` | 放 Apps Script API 網址（**部署後一定要改這個檔案**） |
| `AppsScript_Code.gs.txt` | 後端程式碼，貼到 Google Sheet 的 Apps Script 編輯器 |

---

## 步驟 1：建立 Google Sheet 資料庫

1. 開一份新的 Google Sheet。
2. 把工作表（分頁）改名為 `Cases`（要完全一致，區分大小寫）。
3. 在第一列貼上以下標題（用 Tab 分隔貼上即可自動分欄）：

```
id	title	order_id	order_sn	return_sn	status	return_status	difficulty	updated_at	data_json
```

4. 從網址列複製這份 Sheet 的 ID（網址長這樣：`https://docs.google.com/spreadsheets/d/【這一段就是ID】/edit`）。

之後不用手動填內容，這些欄位都會由 `edit.html` 自動寫入。`data_json` 欄位存放該案件的完整內容（JSON 字串），是實際資料的來源；前面幾欄方便你在 Sheet 上直接瀏覽/搜尋。

## 步驟 2：部署 Apps Script API

1. 在該 Sheet 選單點 **擴充功能 → Apps Script**（或另外建一個獨立的 Apps Script 專案也可以，反正下一步會用 ID 明確指定要打開哪份 Sheet）。
2. 把 `AppsScript_Code.gs.txt` 的內容整段貼進去（取代預設的 `myFunction`）。
3. 把第 13 行 `"貼上你的 Google Sheet ID"` 換成步驟 1 拿到的 Sheet ID。
4. 點右上角 **部署 → New deployment（新增部署作業）**，類型選 **Web app（網頁應用程式）**：
   - Execute as（執行身分）：**Me（我）**
   - Who has access（誰可以存取）：選 **Anyone**
     > ⚠️ 不要選「Anyone within [你的網域]」，這個設定在沒有登入態的 fetch 請求下會被導向登入頁，導致前端讀取一直失敗。這個工具本身也沒有做登入驗證，網域限制實際上沒有多一層防護。
5. 部署後會拿到一組網址，結尾是 `/exec`，複製起來。

> ⚠️ 之後只要改了 Apps Script 程式碼內容，都要「Manage deployments → 編輯 → 版本選 New version → Deploy」重新部署一次，網址通常不變。

## 步驟 3：設定前端 API 網址

打開 `config.js`，把 `API_URL` 換成步驟 2 拿到的 `/exec` 網址。

## 步驟 4：放到 GitHub Pages（或你自己的 http(s) 空間）

1. 建一個 GitHub Repository，把 `list.html`、`detail.html`、`edit.html`、`import.html`、`sop-editor.html`、`style.css`、`config.js` 這 7 個檔案放進去（放在 repo 根目錄，或固定放某個資料夾都可以，只要檔案彼此相對路徑不變）。設定好 SOP 流程之後，`sop_flow.json` 也要放進同一層（見下方「SOP 互動決策樹」章節）。
2. Repo 設定裡開啟 GitHub Pages（Settings → Pages → 選分支/資料夾）。
3. 等 GitHub 產生網址後，把 `https://你的帳號.github.io/repo名稱/list.html` 分享給大家，這就是唯一要給學員的連結。

之後案件內容要更新的話，只要在 Google Sheet 或透過 `edit.html`／`import.html` 改資料就好，**不用重新部署前端網頁**（前端只是純讀取 API，內容都在 Sheet 裡）。只有你改了 HTML/CSS/JS 本身（例如新增功能）時，才需要重新推到 GitHub。

---

## SOP 互動決策樹（全案件共用一份流程）

練習畫面右側「SOP」分頁，會顯示一個累積式的時間軸（accordion）：學員一步步點選問題答案，答過的步驟摺疊顯示「圖示＋問題 → 選了什麼」，點開看完整選項與作答時間；系統自動判讀的節點用 🖥️ 標示、人工判斷用 👤 標示；只有一個選項的節點會自動變成一個醒目的大按鈕（適合模擬「Judge」這種送出動作）。走到結論節點會顯示「✅ 正確處理」或「❌ 不符合SOP」。目前設計是**不評分每一步、只在流程結束時顯示最終結果**。

這份流程是**所有案件共用同一套**，不是每個案件各自一份。內容完全需要你自己輸入——這個工具不知道你們公司實際的判斷邏輯，只負責把你輸入的流程正確跑起來。

**重要：這份資料是靜態檔案 `sop_flow.json`，不是存在 Google Sheet 裡。** 因為完整的 SOP 流程節點數可能很多，容易超過 Google Sheet 單一儲存格 5 萬字元的上限，所以改成跟其他網頁檔案一起放在 GitHub repo 裡，`detail.html` 會直接讀取同資料夾下的 `sop_flow.json`（不透過 Apps Script API，讀取速度也更快、不受 Apps Script 同時執行配額限制）。

### 手動設定（單一或少量節點）

用 `sop-editor.html`（清單頁點「⚙ SOP 流程設定」進入）：
1. 點「載入格式範例」參考結構，或用「上傳檔案」載入現有的 `sop_flow.json`
2. 在文字框編輯 JSON
3. 點「▶ 預覽」可以直接在同一頁測試跑一次，確認分支邏輯、結論文字都正確
4. 確認沒問題後點「⬇ 下載 sop_flow.json」，把下載下來的檔案放到跟 `detail.html` 同一層資料夾，推上 GitHub

### 從正式環境批次匯入、合併多個檔案

如果你是從 DMS 正式環境匯出多個 SOP flow 檔案（例如 SOP1、SOP60、SOP66...幾十個），**不需要一個個手動貼進 sop-editor.html**，用附的 `merge_sop_flows.py` 在自己電腦上跑：

```bash
python3 merge_sop_flows.py --input-dir ./sop_exports --output sop_flow.json
```

把所有匯出的 `.json` 檔案都放進 `./sop_exports` 資料夾（檔名不重要，腳本會自動讀取資料夾內所有 `.json`），執行後會：
- 自動把所有檔案的節點攤平合併成一個集合（節點 id 在正式環境裡本來就是全域唯一的，例如 `SOP60_Node383`，所以不同檔案的節點可以直接接起來）
- 自動判斷流程的起始節點（找「從沒被其他節點指向過」的節點；如果判斷出多個候選，會列出來讓你用 `--start-node` 手動指定）
- 印出還有哪些分支的目標節點沒有出現在你提供的檔案裡（代表可能還缺少對應的匯出檔）

跑完直接就是可以用的 `sop_flow.json`，可以先用 `sop-editor.html` 的「上傳檔案」載入來預覽確認，也可以直接放進 repo 使用。之後 SOP 內容有更新，重新匯出、重跑一次腳本即可，不用透過我或手動編輯。

### 節點格式

- 問題節點：`{ "type": "question", "kind": "system 或 manual", "text": "問題文字", "note": "提示/補充文字（選填，換行用 \n）", "link": { "label": "講義", "url": "https://..." }（選填）, "options": [{ "label": "選項文字", "next": "下一個節點名稱" }, ...] }`
  - `kind` 決定顯示 🖥️（系統判讀）還是 👤（人工判斷），不填預設 manual
  - `options` 只有一個選項時，會自動顯示成一個醒目的大按鈕
- 結論節點：`{ "type": "outcome", "result": "correct 或 incorrect", "text": "結論文字", "note": "補充說明（選填）" }`

## 圖片/影片證據（縮圖 + 點擊放大）

`edit.html` 的 **Buyer Return Info** 跟 **Seller 1st Dispute** 區塊，各有一個「圖片/影片網址」文字框：**每行貼一個圖片網址**（只能貼現成的圖片連結，不支援上傳檔案）。填的時候下方會即時出現小縮圖預覽。

練習畫面（`detail.html`）會把這些網址渲染成縮圖牆，點擊任一張用燈箱放大顯示，點圖片或背景任意處可關閉。

## Chat History / Discuss（模擬對話練習）

`edit.html` 有兩個選填區塊：

- **Chat History**：模擬買賣家/客服/系統的對話紀錄，練習畫面以聊天泡泡呈現（買家、賣家靠左，客服「自己」靠右，系統訊息置中）。
- **Discuss**：模擬客服內部討論筆記，練習畫面用留言串呈現在同一分頁。

沒填的話練習畫面會顯示「此區無資料」。

## 批次匯入多筆案件

用 `import.html`：下載範本 JSON（外層是 `[ ]` 陣列，每個 `{ }` 是一筆完整案件，範本裡也示範了圖片欄位跟 chatHistory/discuss 的格式）→ 貼上或上傳 → 開始匯入，會依序送出每一筆並顯示成功/失敗。同一個 `id` 匯入第二次會直接覆蓋更新。如果你用程式（例如 Python）批次產生案件資料，照範本的 JSON 結構輸出成陣列即可直接匯入。

---

## 已知注意事項

- **公司網路 SSL/Proxy 問題**：如果 fetch 一直失敗，很可能跟你之前處理過的公司網路 SSL inspection 干擾 Google API 連線是同一類問題，可以先換一個網路環境測試排除。
- **30 人同時使用的容量問題**：Apps Script 對「同時執行次數」有配額限制（一般 Google 帳號約 30、Workspace 付費帳號較高）。`AppsScript_Code.gs.txt` 已加上 CacheService 快取（存活 5 分鐘），大部分讀取請求會直接從記憶體回應、不用重新讀 Sheet，大幅降低同時執行的機率，但無法 100% 保證極端同時湧入的情況。前端改放 GitHub Pages 之後，「頁面本身」的讀取完全跟 Apps Script 無關（GitHub Pages 承受再多同時連線都沒問題），只有「讀寫案件資料」這件事還是打 Apps Script，所以風險比之前又更低了一些。
- **同時編輯衝突**：後端邏輯是「用 id 找到列就覆蓋、找不到就新增一列」，沒有做並發鎖定。同時間兩人編輯同一筆案件，後儲存的會蓋掉先儲存的，練習用途應該還好。
- **權限**：目前沒有做登入驗證，只要知道 Apps Script 網址的人都能新增/修改案件內容（不過前端網頁本身可以放在 Private repo + GitHub Pages 存取控制，或至少不公開分享網址，降低被亂改的風險）。
