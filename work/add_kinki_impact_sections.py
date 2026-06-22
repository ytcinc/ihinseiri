from pathlib import Path

PAGES = {
    "mie": {"name": "三重県", "before_h2": "三重県で相談前に整理したいこと"},
    "shiga": {"name": "滋賀県", "before_h2": "滋賀県の生前整理・実家じまいで先に確認すること"},
    "kyoto": {"name": "京都府", "before_h2": "京都府の高齢単身世帯から考える生前整理"},
    "hyogo": {"name": "兵庫県", "before_h2": "兵庫県で相談前に整理したいこと"},
    "nara": {"name": "奈良県", "before_h2": "見積もり相談までの流れ"},
    "wakayama": {"name": "和歌山県", "before_h2": "和歌山県の生前整理・実家じまいで先に確認すること"},
}


def impact_section(pref: str, slug: str) -> str:
    return f"""
    <section id="{slug}-impact" class="section">
      <h2 class="section-title">実家片付けの大変さがわかるインパクト数字</h2>
      <p class="lead">{pref}で遺品整理・生前整理を考えるときは、料金だけでなく、<span class="marker">家財の量、家族だけでかかる時間、親子の気持ちのずれ</span>を先に知っておくことが大切です。数字で見ると、実家の片付けを早めに相談する理由が分かります。</p>
      <div class="grid cols4 metric-grid">
        <div class="card stat-card metric-card impact-card"><span class="metric-label">3LDK一軒家</span><b>1.5〜3トン</b><p class="metric-note">長年住んだ実家では、不用品がトラック3〜5台分になることがあります。</p><span class="metric-sub">家具・布団・家電・物置まで含めて確認</span></div>
        <div class="card stat-card metric-card impact-card"><span class="metric-label">2DKでも</span><b>10〜15m³</b><p class="metric-note">袋ごみだけでは収まりにくく、分別・搬出・車両手配が必要になりやすい量です。</p><span class="metric-sub">退去期限がある部屋は早めに荷物量確認</span></div>
        <div class="card stat-card metric-card impact-card"><span class="metric-label">家族だけだと</span><b>3ヶ月〜半年</b><p class="metric-note">週末ごとに通っても、仕分け・粗大ごみ予約・搬出で長期化しがちです。</p><span class="metric-sub">遠方家族では1年近くかかることも</span></div>
        <div class="card stat-card metric-card impact-card"><span class="metric-label">プロ作業なら</span><b>1〜3日</b><p class="metric-note">一戸建てでも、仕分け・搬出・貴重品探索・写真報告をまとめて進めやすくなります。</p><span class="metric-sub">売却前整理・施設入居前整理に向く</span></div>
      </div>
      <div class="grid cols2" style="margin-top:16px">
        <div class="chart-box">
          <h3>自力整理とプロ作業の時間差</h3>
          <div class="bar-row"><span>1DK 自力</span><div class="bar-track"><div class="bar-fill" style="width:66%"></div></div><b>約1ヶ月</b></div>
          <div class="bar-row"><span>1K プロ</span><div class="bar-track"><div class="bar-fill green" style="width:8%"></div></div><b>1〜3時間</b></div>
          <div class="bar-row"><span>一戸建て 自力</span><div class="bar-track"><div class="bar-fill" style="width:100%"></div></div><b>3ヶ月〜半年</b></div>
          <div class="bar-row"><span>一戸建て プロ</span><div class="bar-track"><div class="bar-fill green" style="width:18%"></div></div><b>1〜3日</b></div>
          <p>{pref}でも、遠方から週末だけ通う整理は長期化しやすく、退去・売却・施設入居の日程がある場合は早めの荷物量確認が重要です。</p>
        </div>
        <div class="chart-box">
          <h3>親子の意識差と費用目安</h3>
          <div class="bar-row"><span>手伝いたい子</span><div class="bar-track"><div class="bar-fill blue" style="width:80%"></div></div><b>約8割</b></div>
          <div class="bar-row"><span>頼みたくない親</span><div class="bar-track"><div class="bar-fill" style="width:60%"></div></div><b>約6割</b></div>
          <div class="bar-row"><span>1R</span><div class="bar-track"><div class="bar-fill green" style="width:18%"></div></div><b>3万〜8万円</b></div>
          <div class="bar-row"><span>一戸建て</span><div class="bar-track"><div class="bar-fill" style="width:88%"></div></div><b>22万〜70万円以上</b></div>
          <p>生前整理は家を空にする作業ではありません。<span class="marker">通帳・印鑑・権利書・保険証券・写真・形見分け品</span>を家族で共有しておくと、遺された家族の負担を減らせます。</p>
        </div>
      </div>
    </section>
"""


def ensure_impact_css(html: str) -> str:
    if ".impact-card" in html:
        return html
    css = (
        ".impact-card{border-top-color:var(--green)}"
        ".impact-card b{font-size:38px}"
        ".impact-card .metric-label{background:var(--green)}"
        ".impact-card .metric-sub{color:var(--green)}"
    )
    if "@media(max-width" in html:
        return html.replace("@media(max-width", css + "\n    @media(max-width", 1)
    return html.replace("</style>", css + "\n  </style>", 1)


def main() -> None:
    root = Path.cwd()
    for slug, info in PAGES.items():
        path = root / slug / "index.html"
        html = path.read_text(encoding="utf-8")
        if "実家片付けの大変さがわかるインパクト数字" in html:
            print(f"skip existing: {slug}")
            continue
        html = ensure_impact_css(html)
        h2 = f'<h2 class="section-title">{info["before_h2"]}</h2>'
        h2_pos = html.find(h2)
        if h2_pos < 0:
            raise SystemExit(f"h2 marker not found for {slug}: {h2}")
        section_pos = html.rfind("<section", 0, h2_pos)
        if section_pos < 0:
            raise SystemExit(f"section start not found for {slug}: {h2}")
        html = html[:section_pos] + impact_section(info["name"], slug) + "\n" + html[section_pos:]
        path.write_text(html, encoding="utf-8")
        print(f"updated: {slug}")


if __name__ == "__main__":
    main()
