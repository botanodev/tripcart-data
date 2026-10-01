# tripcart-data

出國購物計算機（`com.botano.tripcart`）讀取的公開資料。App 唯一的網路請求就是讀這裡的 JSON。

| 檔案 | 內容 | 更新方式 |
|---|---|---|
| `rates.json` | 每日參考匯率（USD 為基準） | GitHub Actions 每天 UTC 01:00 自動更新 |
| `tax-reference.json` | 各國消費稅參考值 | 人工維護（**尚未建立**） |

App 讀取的網址：`https://raw.githubusercontent.com/tnth/tripcart-data/main/rates.json`

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
