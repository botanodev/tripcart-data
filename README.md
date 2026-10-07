# tripcart-data

出國購物計算機（`com.botano.tripcart`）讀取的公開資料。App 唯一的網路請求就是讀這裡的 JSON。

| 檔案 | 內容 | 更新方式 |
|---|---|---|
| `rates.json` | 每日參考匯率（USD 為基準） | GitHub Actions 每天 UTC 01:00 自動更新 |
| `tax-reference.json` | 各國消費稅參考值 | **人工維護**：在 GitHub 網頁上直接改（見下方） |

App 讀取的網址：
- `https://raw.githubusercontent.com/tnth/tripcart-data/main/rates.json`
- `https://raw.githubusercontent.com/tnth/tripcart-data/main/tax-reference.json`（失敗時改走 jsDelivr 鏡像）

> **這個 repo 必須保持公開、名稱與分支不能改。** 網址寫死在已發布的 App 裡，
> 改了之後舊版 App 抓不到資料（會退回備援來源，不會壞，但不該這樣）。

## rates.json

```json
{
  "schemaVersion": 1,
  "date": "2026-10-12",
  "generatedAt": "2026-10-12T01:03:22Z",
  "base": "USD",
  "source": "fawazahmed0",
  "rates": { "USD": 1, "JPY": 148.2, "TWD": 32.1 }
}
```

- `rates`：1 USD 可換多少該貨幣。代碼一律大寫 ISO 4217
- 格式**只增不減**；App 忽略不認識的欄位
- `source` 是 `fawazahmed0` 或 `open.er-api`。若為後者，App 設定頁須依其條款標示來源

## tax-reference.json（人工維護）

各國的消費稅率、標價是否含稅、常見的退稅方式。App 在旅程第一次用到某個貨幣時帶入，
畫面上一律標「參考值，可能與實際不同」，使用者可以自己改。

### 怎麼改（只要瀏覽器，不用開發環境）

1. 在 GitHub 打開這個檔案，按右上角的鉛筆圖示
2. 改數字或加國家（照現有的格式複製一行改）
3. **把 `updatedAt` 改成今天的日期**——App 用它判斷哪一份比較新，**沒改日期 App 不會採用**
4. 按「Commit changes」

App 每 7 天抓一次，抓到較新的版本後**下次打開 App** 生效。已經建立的旅程不受影響（那趟的稅率在第一次用那個貨幣時就記下了），只有之後新用到的貨幣套用新值。

### 格式

```json
{ "country": "JP", "currency": "JPY", "taxRate": "0.10", "priceIncludesTax": true, "refundMode": "departure", "touristRefund": true }
```

| 欄位 | 說明 |
|---|---|
| `country` | 國家代碼（ISO 3166，兩碼大寫） |
| `currency` | 貨幣代碼（ISO 4217）。**同一個貨幣出現在兩個以上國家**（例如 EUR）時 App 不會自動帶入，讓使用者自己填 |
| `taxRate` | 稅率，**用字串**寫小數：`"0.10"` 是 10%。沒有單一稅率（例如美國）就整欄拿掉 |
| `priceIncludesTax` | 標價是否已含稅（`true`／`false`） |
| `refundMode` | 常見退稅方式：`departure`（出境時退）、`instant`（當場扣）、`none`。App **不會預選**，只做參考 |
| `touristRefund` | 該國有沒有觀光客退稅 |

### 改壞了會怎樣

少一個逗號、引號這類格式錯誤：App 會發現檔案讀不懂而**不採用**，繼續用手上那份，不會壞。
但數字本身打錯（例如 `"0.01"` 打成 `"0.10"`）App 分辨不出來，會照用——改完請再看一次。

> App 安裝包裡也附一份（`tripcart` 專案的 `assets/tax-reference.json`）。出新版 App 前，
> 在專案裡跑 `python tool/pull_tax_reference.py` 把這裡的版本複製過去，兩邊才會一致。

## 每日流程（`scripts/update_rates.py`）

1. 依序嘗試：fawazahmed0（jsDelivr）→ fawazahmed0（Cloudflare Pages 鏡像）→ open.er-api.com
2. 驗證：核心貨幣（USD EUR JPY KRW TWD CNY HKD GBP THB SGD AUD）都在且為正數、USD 為 1
3. **驗證失敗就不寫入**，保留前一天的檔案；該次執行顯示為失敗（紅色）
4. 上游日期比現有檔案舊時不覆蓋
5. 只有內容真的變了才 commit

本機測試：`python -m unittest discover -s scripts -v`

## 已知限制

GitHub 會在公開 repo **60 天沒有任何活動**時自動停用排程。這個 repo 幾乎每天都有
自動 commit，正常不會觸發；若匯率連續 60 天完全沒變（不太可能），要到 Actions 頁面重新啟用。
