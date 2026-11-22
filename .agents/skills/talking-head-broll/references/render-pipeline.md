# 渲染原理與一定會踩的坑

範本：`projects/example-talking-head/composition/index.html`（Hyperframes 0.9.19）

## 一個檔案、三種輸出

`composition/index.html` 是完整版（原片＋圖卡＋插畫＋字幕）。`prepare-composition.py --mode` 會另外產生：

| 模式 | 資料夾 | 內容 | 渲染成 |
|---|---|---|---|
| （預設） | `composition/` | 全部 | `<名稱>-合成.mp4` |
| `overlay` | `composition-overlay/` | 拿掉原片和字幕，背景透明 | `output/broll/overlay-full.webm` → 切成各段 |
| `captions` | `composition-captions/` | 只留字幕，背景透明 | `output/broll/captions.webm` |

`composition-*` 資料夾的字型、GSAP、樣式是捷徑（symlink）指回 `composition/`，不進 Git。
`render-all.sh` 會依序全部做完。

## HTML 結構（照範本）

```html
<div id="root" class="mode-composite" data-composition-id="main" data-start="0" data-duration="<長度>" data-width="1080" data-height="1920">
  <video id="footage" class="clip layer" src="<原片>" data-start="0" data-duration="<長度>" data-has-audio="true" playsinline></video>
  <section id="bandA" class="clip layer" data-start=… data-duration=…> 圖卡段 </section>
  <section id="c1" class="clip layer" data-start=… data-duration=…> 插畫 B-roll </section>
  <div id="captions" class="clip layer" data-start="0" data-duration="<長度>"><!-- CAPTIONS:BEGIN --><!-- CAPTIONS:END --></div>
</div>
```
- 連續的圖卡段共用一條「背景帶」section（例：夜空帶 7.85–31.29），避免背景每段重新淡入。
- 時間一律寫原片秒數（words.json），不用相對時間。
- 動畫用 `styles/zodiac.js` 這類共用小工具（starfield、fadeUp、pop、tagIn），全部可跳秒。

## 一定會踩的坑（都踩過）

| 症狀 | 原因 | 解法 |
|---|---|---|
| 透明片段裡還是有原片 | Hyperframes 會把 `<video>` 另外解碼合成，CSS `opacity:0`／`display:none` 擋不住 | 透明版本直接從 HTML 拿掉 `<video>`（prepare `--mode` 已處理） |
| 透明 WebM 其實不透明 | 根元素背景沒變透明 | 根元素一定要寫 `class="mode-composite"`；prepare 只換這個 class 屬性（不能用「第一個出現的字串」，註解裡也有同樣的字） |
| 只有字幕的版本跑不動 | 畫面段落被拿掉，程式找不到元素 | 畫面動畫程式包在 `if (document.querySelector("section")) { … }` |
| check 報一堆 content_overlap | 全螢幕插畫蓋在圖卡上 | 插畫期間 `tl.set("#bandB", {opacity:0}, 起)`、結束時設回 1 |
| 第 0 格看不到東西 | 用 `tl.set(…, 0)` 設初始狀態 | 初始隱藏用 `gsap.set`；第 0 格要有背景或標題（縮圖） |
| 星點超框警告 | 裝飾元素超出容器 | 星空容器加 `data-layout-ignore` |
| 註腳太小警告 | 手機可讀下限 28px | 所有字 ≥ 28px |
| 關鍵字放大後一行放不下 | 1.75 倍字寬 | project.json `caption.line_units`，prepare 會自動縮字 |
| 特效元件從 CDN 載 GSAP | registry 元件預設用 jsdelivr | 改用 `vendor/gsap.min.js` |
| CSS keyframes 動畫跳格 | 渲染時逐格跳秒，CSS 動畫不跟時間軸 | 改成 GSAP 時間軸驅動（例：grain-overlay） |
| OpenCV 5 沒有 CascadeClassifier | 5.0 拿掉了 | `pip install "opencv-python-headless<5"` |

## 時間

59 秒影片（4 核心雲端機器）：合成 MP4 約 5 分、透明圖卡層約 6 分、字幕層約 2 分、切段約 3 分。
透明 WebM 比 MP4 慢；改動只影響動畫時用 `render-all.sh <專案> --skip-composite`。
