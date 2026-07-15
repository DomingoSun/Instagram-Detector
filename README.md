# Instagram Reels 發佈前政策檢查器

給**自己製作影片的創作者**用的發佈前自我檢查工具：在發佈 Reels 之前，
掃描你的文案、hashtag、口白逐字稿，找出可能**違反 Instagram 政策**、
導致**限流（不被推薦、觸及下降）**或**下架/帳號處分**的內容。
支援中文與英文，純 Python 標準庫、零依賴。

> ⚠️ 免責聲明：Instagram 不公開演算法細節，政策執行也會隨時間變動。
> 本工具依據公開的社群守則（Community Guidelines）與推薦準則
> （Recommendation Guidelines）整理常見風險樣式，**通過檢查不代表保證
> 不被限流**，僅作為發佈前的自我檢查輔助。

## 檢查什麼

風險分成三種後果（consequence）：

| 後果 | 意義 | 依據 |
| --- | --- | --- |
| `removal` | 內容下架、帳號警告/停權 | 社群守則：管制商品、博弈推廣、保證獲利、成人導流、暴力威脅、自殘、危險挑戰、買粉刷量 |
| `reach` | 不被推薦到 Reels/探索頁 = 限流 | 推薦準則：互動誘餌（按讚+分享才能抽）、誇大健康/減肥宣稱、性暗示擦邊、標題黨、搬運/浮水印、互粉互讚、站外導流、hashtag 問題 |
| `quality` | 不罰但需注意的最佳實務 | 例如業配內容記得開「付費合作關係」標籤 |

Hashtag 專項檢查：

- 超過 30 個（IG 硬上限，可能無法發佈）
- 超過 10 個（垃圾訊號；官方建議 3–5 個）
- 使用曾被回報封鎖/限制的 hashtag（內建節錄清單，可自行維護）
- 重複標籤

另外會附上**人工檢查清單**——文字掃不到、但實際影響推薦的項目：
其他平台浮水印（TikTok logo）、音樂版權、畫面中的菸酒/賭博/裸露元素、
內容原創性、誤導性封面。

## 判定等級與 exit code

| 判定 | 意義 | exit code |
| --- | --- | --- |
| `pass` | 未發現問題 | 0 |
| `review` | 小問題，建議調整 | 0 |
| `reach_risk` | 有被限流的風險 | 1 |
| `violation_risk` | 可能違反社群守則（下架/帳號處分） | 2 |

## 安裝

```bash
pip install -e ".[dev]"
```

Python ≥ 3.9，無執行期依賴。

## 使用方式

```bash
# 直接檢查文案（#hashtag 會自動解析）
reels-safety --caption "按讚+分享+標記3個朋友就抽AirPods！#f4f #tagsforlikes"

# 檢查完整內容（文案 + 逐字稿 + hashtag）
reels-safety --json-file examples/risky_reel.json

# 機器可讀輸出
reels-safety --json-file examples/risky_reel.json --format json

# 從管線輸入
echo "7天瘦5公斤 保證有效" | reels-safety --stdin
```

輸出範例：

```
判定:     ⚠️ 限流風險 — 內容可能不被推薦、觸及下降
風險分數: 61/100

發現的問題:
  [高｜限流] 誇大健康/減肥療效宣稱，屬於「不可推薦內容」…
      位置: caption  證據: '🔥7天瘦5公斤！保證有效！'
      建議: 改用個人經驗描述（「我自己三個月的變化」）並避免保證性字眼與具體數字承諾
  [中｜限流] 互動誘餌（要求按讚/留言/分享/標記朋友換獎勵）…
      建議: 抽獎可以辦，但避免「按讚+分享才能抽」句式…

發佈前人工檢查清單（文字掃不到的部分）:
  □ 影片是否帶有其他平台浮水印（TikTok logo 等）？…
  □ 背景音樂是否來自 IG 音樂庫或已取得授權？…
```

## JSON 輸入格式

```json
{
  "caption": "文案（可含 #hashtag）",
  "hashtags": ["另外要加的標籤"],
  "audio_transcript": "影片口白逐字稿",
  "comments": ["要一併檢查的留言"],
  "url": "（選填）",
  "author_username": "（選填）"
}
```

所有欄位皆選填，有什麼就檢查什麼。

## 程式庫用法

```python
from reels_safety import ReelContent, analyze

result = analyze(ReelContent(caption="按讚+分享就抽獎 #tagsforlikes"))
print(result.verdict.value)   # "reach_risk"
print(result.risk_score)      # e.g. 44
for det in result.detections:
    print(det.consequence.value, det.message)
    print(" →", det.suggestion)
```

## 評分方式

每條命中規則依嚴重度加權（低 8、中 18、高 35、嚴重 60），同一規則在
同一欄位只計一次，總分上限 100。判定邏輯：

- 任何「下架」類的高/嚴重命中 → `violation_risk`
- 「限流」類有中/高命中，或限流加權 ≥ 30 → `reach_risk`
- 只有低度提示 → `review`
- 無命中 → `pass`

門檻在 `analyzer.py`，規則與受限 hashtag 清單在 `rules.py`，皆可自行調整。

## 執行測試

```bash
python -m pytest
```

## Roadmap

- 受限 hashtag 清單自動更新（爬取標籤頁狀態）
- LLM 語意判斷，補足規則比對抓不到的隱晦表述
- 影格分析：浮水印、畫面元素（菸酒/裸露）偵測
- 批次檢查 + 報表輸出
