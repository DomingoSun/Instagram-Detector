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

## 🎬 影片檢測版（上傳影片、標出幾分幾秒）

`docs/video.html` 是上傳影片版：選擇影片檔（mp4/mov/mp3/wav…）後，在瀏覽器內辨識
**口白**與**畫面上的文字**，套用同一套規則引擎，輸出：

- 整體判定與風險分數（口白＋畫面文字＋文案合併評估）
- **需優化的字詞清單（依時間排序）**：`🎙️ 00:06–00:14 命中「七天瘦五公斤」→ 建議…`，
  每筆標示來源（🎙️口白／🖼️畫面文字／📝文案），點時間戳可直接跳轉影片該秒數播放
- 口白逐字稿與畫面文字列表（命中段落黃底標示）
- 發佈前人工檢查清單

三種辨識/檢測來源：

1. **口白**：用 [Whisper](https://github.com/openai/whisper) 語音辨識模型
   （transformers.js，純前端）轉出帶時間戳的逐字稿
2. **畫面文字（OCR）**：勾選後每 2 秒抽一張影格，用 [Tesseract.js](https://tesseract.projectnaptha.com/)
   （繁中＋英文，純前端）辨識字卡/字幕，連續同一張字卡會合併成一個時間區間
3. **貼文文案**：選填，一併比對

### 🤖 AI 深度分析（選配）

收合區塊「AI 深度分析」可把逐字稿、畫面文字與文案送給 LLM 做語意層面的審查，
抓出關鍵字比對漏掉的**隱晦說法**，並產出「原說法 → 安全替代說法」報告：

- 支援 **Anthropic（Claude Opus 4.8）** 或 **OpenAI（GPT-4o mini）**，使用者自備 API key
- **⚠️ 隱私差異**：預設的口白/OCR/規則檢測全部在本機執行、影片不上傳；但一旦使用此
  選配功能，**上述文字內容會傳送到所選供應商的伺服器**。不使用則不受影響。
- API key 僅保存在使用者的瀏覽器（可選 localStorage），不經過任何中間伺服器

注意事項：

- 影片與辨識**預設全部在本機執行、不上傳任何伺服器**；第一次使用需下載模型
  （Whisper tiny 約 40MB／base 約 80MB／small 約 250MB；Tesseract 繁中語言包約數 MB，之後快取）
- 語音/OCR 輸出常為簡體中文，`detector.js` 內建簡→繁正規化後再比對規則
- 辨識會有錯字與時間誤差，模型越大越準；OCR 對花俏字體/動態字卡準度有限（燒錄字幕效果最好）
- 長影片辨識時間依裝置效能而定；建議桌面版 Chrome/Edge

## 線上版（GitHub Pages）

`docs/` 內含免安裝的網頁版（純前端，檢測全部在瀏覽器本地執行，不會上傳資料），
可直接用 GitHub Pages 部署分享給其他人測試：

1. 到 repo 的 **Settings → Pages**
2. Source 選 **Deploy from a branch**，選擇分支與 `/docs` 資料夾，儲存
3. 一兩分鐘後網址就會生效：`https://<帳號>.github.io/Instagram-Detector/`

> 注意：私人 repo 要 GitHub Pro/團隊方案才能開 Pages，公開 repo 免費。
> 網頁版是 `docs/detector.js` 的 JS 移植，規則以 Python 版
> （`src/reels_safety/rules.py`）為準，兩邊修改時需同步。

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
