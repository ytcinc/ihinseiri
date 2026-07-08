# 大阪市24区ページ 区固有差し替え 検査チェックリスト

北区 `osaka/kita/index.html` を「正（テンプレ）」とし、各区は北区を複製して
**区固有ブロックだけ**を差し替える。以下は全区共通の検査基準。

## 差し替え対象 34項目（すべて区で置換されているべき箇所）

| # | 箇所 | class/id・要素 | 北区 行(目安) | 種別 |
|---|---|---|---|---|
| 1 | title | `<title>` | 6 | 区名 |
| 2 | **meta description** | `meta[name=description]` | 7 | 区名＋地名 |
| 3 | og:description（head） | `meta[property=og:description]` | 8 | 区名＋地名 |
| 4 | canonical | `link[rel=canonical]` | 2158 | slug |
| 5 | JSON-LD パンくず | BreadcrumbList name/item | 2181-2182 | 区名/slug |
| 6 | JSON-LD FAQ | Question name×9・geo answer×4 | 2192-2299 | 区名＋地名 |
| 7 | JSON-LD 記事 | Article headline/description/@id | 2307-2334 | 区名＋地名/slug |
| 8 | og:title | `meta[property=og:title]` | 2358 | 区名 |
| 9 | twitter:title | `meta[name=twitter:title]` | 2359 | 区名 |
| 10 | og:description（2枚目） | `meta[property=og:description]` | 2360 | 区名＋地名 |
| 11 | og:url | `meta[property=og:url]` | 2362 | slug |
| 12 | twitter:description | `meta[name=twitter:description]` | 2363 | 区名＋地名 |
| 13 | JSON-LD 事業者 | ProfessionalService @id/name/url/areaServed（**住所は共通で不変**） | 2415-2430 | 区名/slug |
| 14 | ロゴ alt | `img.global-brand-mark[alt]` | 2588 | 区名 |
| 15 | パンくず（可視） | `nav.breadcrumb` | 2608 | 区名 |
| 16 | キッカー | `p.kita-kicker` | 2613 | 区名 |
| 17 | H1 | `h1` | 2614 | 区名 |
| 18 | 冒頭アラート | `.kita-alert`（相談先に迷う場合） | 2619 | 区名 |
| 19 | ページ内ナビ | `nav.kita-article-nav[aria-label]` | 2629 | 区名 |
| 20 | **リード文** | `p.kita-lead`×4（p1・p2共通／**p3=区名・p4=地名**） | 2615-2618 | 区名＋地名 |
| 21 | **data-strip 4枠** | `.kita-data-strip`（①②③統計／④工場名） | 2620-2624 | 統計→[要収集]＋工場 |
| 22 | セクション1 | `#comparison-guide` 冒頭p（統計）＋カード（自己搬入先工場） | 2644, 2647 | 統計＋区名＋工場 |
| 23 | **地域事情** | `#area-context` h3＋p×3 | 2666-2669 | 地名描写 |
| 24 | **エリア表** | `table.kita-table` 区固有4行（+遠方＝共通） | 2670-2677 | 地名 |
| 25 | **相談ケース** | h3＋`article.kita-card`×3（+遠方立会い＝共通） | 2678-2683 | 地名 |
| 26 | ごみガイド | `#garbage-guide` 環境事業センター名/電話・区名・工場・地域包括 | 2688-2815 | センター＋区名＋工場 |
| 27 | 適正処理困難物 | `#difficult-waste` 区名ラベル・工場持込先 | 2817-2841 | 区名＋工場 |
| 28 | 分け方 | `#decision` h2/p | 2843-2846 | 区名 |
| 29 | 料金差 | `#cost-detail` h2/alert | 2892-2904 | 区名 |
| 30 | **FAQ** | `#faq` h2＋区名設問3＋地名設問3 | 2938-2948 | 区名＋地名 |
| 31 | 近隣エリア | `#related` p＋隣接区リンク | 2952-2965 | 区名＋隣接区 |
| 32 | 監修/おわりに | `#supervisor` p・`#closing-message` alert | 2972, 2981 | 区名 |
| 33 | サイドバー | `aside.kita-side` aria-label・要点統計・ごみガイド・区役所リンク・工場リンク | 2986-3011 | 区名＋統計＋工場 |
| 34 | フッター | `.footer-inner` | 3106 | 区名 |

## 据え置きリスト（共通・1バイトも変えない）

- CSS 全ブロック（`<head>` 内の全 `<style>`、class/id 名）
- セクション `#price`（料金目安）・`#check`（写真準備）・`#flow`（ステップ）
- 粗大ごみ／適正処理困難物の**大阪市共通ルール**（30cm基準・手数料・受付センター番号 0120-79-0053 等）
- **表5行目「遠方からのご対応」**（`#area-context` table 最終行）
- **カード3枚目「遠方からの立会いなし整理」**（`#area-context` の3枚目）
- ProfessionalService の**住所**（共通HQ：`postalCode 530-0002` / `addressLocality 大阪市北区` / `曾根崎新地2丁目6-23 MF桜橋ビル`）
- 舞洲破砕設備（破砕は全区共通の施設）

## 検査ルール

1. **統計 data-strip 4枠**：①②③は全区 `[要収集]`（数値は創作しない）、④は裏取りした工場名。
2. **持込工場・環境事業センター・隣接区**：現行ページ＋公式データで裏取り。確認できなければ `[要確認]`（推測で書かない）。
3. **残存チェック（grep）**：
   - 北区由来の地名（`梅田|中之島|天満|中崎町|中津|天神橋|大江橋|渡辺橋|堂島|北新地|大深町|扇町|長柄|本庄|大淀|大阪駅|大阪梅田`）→ 0件
   - 北区の旧統計（`23,734|18\.3|11\.1|11,400`）→ 0件
   - 他区の工場名の誤混入（例：此花=舞洲工場のとき `東淀工場|西淀工場` が無いこと）
   - **現行ページ由来の旧地名**（芯に無い旧町名。例：此花の `梅香|春日出|島屋`）→ 0件
4. **意図した「北区」残存（誤検出しない）**：
   - `addressLocality: 大阪市北区`（#13 共通HQ住所）
   - 環境事業センターの担当区域に北区が含まれる区（例：東北担当の都島区で「北区・都島区・淀川区・東淀川区」）
   - 隣接区リンクに北区を持つ区（例：都島・中央の `/osaka/kita/`）
5. **CSS健全性**：`<style>` open/close 各20・入れ子なし（1206行で閉じる）。

## 進捗（統計は全区 [要収集] 保留）

| 区 | slug | 工場 | 環境事業センター | 隣接区 | 検査 |
|---|---|---|---|---|---|
| 福島区 | fukushima | 西淀工場 | 西北 06-6477-1621 | 北区・此花区・西区・淀川区 | 合格 |
| 都島区 | miyakojima | 東淀工場 | 東北 06-6323-3511 | 北・城東・旭・中央・淀川・東淀川・福島 | 合格 |
| 此花区 | konohana | 舞洲工場 | 西北 06-6477-1621 | 大正・西・浪速・福島・西淀川・住之江 | 合格 |
