import re
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import streamlit as st
import pandas as pd
import io
import os
import warnings
import random as _rnd

# アルゴリズム,計算量の理解、全体の計算量の表示、現実的に計算できるノード数、描画手法、Github、サポーターズ


# ご提示いただいたコードで使用している3つの主要アルゴリズムについて、**「何をしているのか（ロジック）」**と**「なぜその計算量になるのか（数学的根拠）」**を、物流の現場に例えて分かりやすく解説します。

#  は拠点数（Nodes）、 はルート数（Edges）を表します。
 
#  強橋検出O(E × (V+E))

# カスケード故障検出O(V × (V+E))

# 迂回コスト分析O(V × E)

# ---

# ### 1. 強橋（Strong Bridge）検出

# **計算量:** 

# このアルゴリズムは、**「総当たりシミュレーション方式（ナイーブ法）」**を採用しています。

# #### 📦 アルゴリズムの仕組み（ロジック）

# 1. ネットワーク内の**すべてのルート（辺）をリストアップ**します。
# 2. その中からルートを**1本だけ一時的に「通行止め（削除）」**にします。
# 3. その状態で、「出発地（）」から「到着地（）」へ、**迂回路を使ってたどり着けるか**（到達可能性判定）をチェックします。
# * もし**たどり着けない**なら、そのルートは「強橋（なくなると困る道）」です。
# * たどり着けるなら、ただの「冗長な道」です。


# 4. 通行止めを解除し、次のルートで同じことを繰り返します。

# #### 📐 計算量の内訳

# * **外側のループ:** 全ルートを試すので、 回繰り返します。
# * **内側の処理:** 「たどり着けるか？」のチェックには、幅優先探索（BFS）または深さ優先探索（DFS）を使います。これらはグラフ全体を走査するため、 かかります。
# * **合計:** 

# > **ポイント:**
# > 本来、橋の検出は  という超高速な手法（Tarjan法など）もありますが、それは「無向グラフ」用です。「有向グラフ」で正確に行うには実装が非常に複雑になるため、今回は**数百〜数千ノード規模なら十分高速で、かつ実装ミスが起きにくいこの「総当たり法」**を採用しています。

# ---

# ### 2. カスケード故障（Cascade Failure）検出

# **計算量:** 

# これは**「上流依存性のチェック」**です。「自分は壊れていないが、供給元が全滅したので仕事ができない」状態を探します。

# #### 📦 アルゴリズムの仕組み（ロジック）

# 1. **生き残っているすべての拠点**を順番にチェックします。
# 2. 各拠点について、**「自分に荷物を送ってくれる可能性のあるすべての先祖（上流拠点）」**をリストアップします。
# * NetworkXの `nx.ancestors` 関数を使用。


# 3. もし、「上流拠点」が存在するのに、その**すべてが「故障中（孤立）」**リストに入っていた場合、その拠点も「カスケード故障（連鎖的な機能不全）」と判定します。

# #### 📐 計算量の内訳

# * **外側のループ:** 全拠点をチェックするので、 回繰り返します。
# * **内側の処理:** `nx.ancestors` は、ある地点から矢印を逆向きにたどって行けるところまで行く探索（BFS/DFS）を行います。最悪の場合、グラフ全体をなめるので  かかります。
# * **合計:** 

# > **ポイント:**
# > 直前の親だけでなく「ずっと上の親」まで遡るため、計算量は重めになりますが、これにより「大元の工場が止まったら、その下請けの下請けも止まる」といった深い連鎖を検出できます。

# ---

# ### 3. 迂回コスト分析

# **計算量:** 対象ルート数  または 
# ※ プロンプトの  は、単純なBFSを全拠点で行った場合の概算ですが、今回のコード（重み付きグラフ）では**ダイクストラ法**の計算量が適用されます。

# これは**「カーナビのルート再検索」**と同じです。

# #### 📦 アルゴリズムの仕組み（ロジック）

# 1. **「障害で通れなくなったルート（）」**だけをリストアップします。
# 2. **障害が起きる前**のグラフで、 から  への最短経路（ダイクストラ法）を計算します。
# 3. **障害が起きた後**のグラフで、同じく  から  への最短経路を計算します。
# 4. その差額（コスト増）を計算します。

# #### 📐 計算量の内訳

# * **外側のループ:** 「停止させたルートの本数」だけ繰り返します（最大で  回ですが、通常は数本）。
# * **内側の処理:** 重み付きグラフの最短経路探索には**ダイクストラ法**が使われます。
# * 効率的な実装（バイナリヒープ使用）の場合、1回の計算量は  です。


# * **合計:** 停止ルート数  とすると、。

# > **ポイント:**
# > もし「重み（距離）」がない単純なグラフならBFSで済むため  になります。
# > 今回のコードは将来的な「距離コスト」の導入を見越して、重み対応の関数（`shortest_path_length`）を使っているため、少しリッチな計算量になっています。

# ---

# ### まとめ：SIer面接での回答例

# もし面接で「このツールの計算量は？」と聞かれたら、こう答えると完璧です。

# | アルゴリズム | 計算量 | SIer的な説明 |
# | --- | --- | --- |
# | **強橋検出** |  | 「ナイーブな総当たり法を採用しました。有向グラフ専用の高速アルゴリズムは実装リスクが高いため、**保守性と正確性を優先**し、数千ノード規模で実用十分なこの手法を選びました。」 |
# | **カスケード故障** |  | 「各拠点から逆方向探索（Ancestors探索）を行い、上流の生存確認を行っています。**供給網の断絶リスクを網羅的に洗い出す**ための設計です。」 |
# | **迂回コスト** |  | 「標準的な**ダイクストラ法**を用いています。障害が発生した特定のエッジに対してのみ再計算を行うため、レスポンスは高速です。」 |
#                                      ↑ 辺重みなしだと幅優先探索と同じ


# ---------------------------------------------------------------------------
# 日本語フォント設定（多段階フォールバック）
# ---------------------------------------------------------------------------
import matplotlib


def setup_japanese_font():
    try:
        import japanize_matplotlib  # noqa: F401
        return "japanize-matplotlib"
    except ImportError:
        pass

    from matplotlib import font_manager
    font_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansCJKjp-Regular.otf")
    if os.path.exists(font_path):
        font_manager.fontManager.addfont(font_path)
        prop = font_manager.FontProperties(fname=font_path)
        matplotlib.rcParams["font.family"] = prop.get_name()
        return "bundled-font"

    candidates = [
        "Noto Sans CJK JP", "Noto Sans JP",
        "IPAexGothic", "IPAGothic",
        "Hiragino Sans", "Hiragino Kaku Gothic ProN",
        "Yu Gothic", "Meiryo", "MS Gothic",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            matplotlib.rcParams["font.family"] = name
            return f"system:{name}"

    warnings.warn("日本語フォントが見つかりません。")
    return "fallback"


_font_status = setup_japanese_font()
matplotlib.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------------------
# ページ設定
# ---------------------------------------------------------------------------
st.set_page_config(page_title="物流ネットワーク障害シミュレーター", layout="wide")


# ---------------------------------------------------------------------------
# デモシナリオ定義
# ---------------------------------------------------------------------------
DEMO_SCENARIOS = {
    "シナリオ1: 関東主要物流ネットワーク — 末端依存の強橋": {
        "description": (
            "東京・横浜・千葉・さいたまを中核とする関東17拠点ネットワーク（距離はkm）。"
            "主要拠点間は複数の迂回路で冗長化されているが、"
            "**長野・静岡・甲府** は単一ルートでしかつながっておらず強橋として検出される。"
            "「どこを冗長化すれば全体の耐障害性が上がるか」を特定するための実践的な分析例。"
        ),
        "recommend_mode": "強橋分析（単一障害点の特定）",
        "nodes": [
            "東京", "横浜", "千葉", "さいたま", "八王子", "海老名",
            "厚木", "川越", "鶴ヶ島", "高崎", "宇都宮", "成田",
            "つくば", "御殿場", "甲府", "長野", "静岡",
        ],
        "edges": [
            ("東京",    "横浜",    30), ("横浜",    "東京",    30),
            ("東京",    "千葉",    40), ("千葉",    "東京",    40),
            ("東京",    "さいたま",  25), ("さいたま",  "東京",    25),
            ("横浜",    "海老名",   20), ("海老名",   "横浜",    20),
            ("海老名",   "厚木",    10), ("厚木",    "海老名",   10),
            ("厚木",    "八王子",   30), ("八王子",   "厚木",    30),
            ("八王子",   "東京",    40), ("東京",    "八王子",   40),
            ("さいたま",  "川越",    20), ("川越",    "さいたま",  20),
            ("川越",    "鶴ヶ島",   10), ("鶴ヶ島",   "川越",    10),
            ("鶴ヶ島",   "高崎",    60), ("高崎",    "鶴ヶ島",   60),
            ("高崎",    "宇都宮",   80), ("宇都宮",   "高崎",    80),
            ("宇都宮",   "さいたま",  90), ("さいたま",  "宇都宮",   90),
            ("千葉",    "成田",    40), ("成田",    "千葉",    40),
            ("成田",    "つくば",   50), ("つくば",   "成田",    50),
            ("つくば",   "東京",    60), ("東京",    "つくば",   60),
            ("厚木",    "御殿場",   50), ("御殿場",   "厚木",    50),
            ("八王子",   "甲府",    70), ("甲府",    "八王子",   70),
            ("川越",    "八王子",   30), ("八王子",   "川越",    30),
            ("海老名",   "八王子",   25), ("八王子",   "海老名",   25),
            ("つくば",   "宇都宮",   70), ("宇都宮",   "つくば",   70),
            ("高崎",    "長野",    100), ("長野",    "高崎",    100),
            ("御殿場",   "静岡",    60), ("静岡",    "御殿場",   60),
        ],
        "highlight": "高崎↔長野・厚木↔御殿場↔静岡・八王子↔甲府 が強橋として検出される",
    },
    "シナリオ2: 関東主要物流ネットワーク — 中継拠点停止と末端孤立": {
        "description": (
            "**御殿場** は厚木↔静岡を結ぶ唯一の中継拠点。"
            "御殿場が停止すると、静岡は入次数・出次数がともに0になり完全孤立する。"
            "同様に八王子停止→甲府孤立、高崎停止→長野孤立が発生する。"
            "「中継拠点が単一障害点になっている」構造の危険性を示す。"
        ),
        "recommend_mode": "障害シミュレーション（影響範囲の確認）",
        "nodes": [
            "東京", "横浜", "千葉", "さいたま", "八王子", "海老名",
            "厚木", "川越", "鶴ヶ島", "高崎", "宇都宮", "成田",
            "つくば", "御殿場", "甲府", "長野", "静岡",
        ],
        "edges": [
            ("東京",    "横浜",    30), ("横浜",    "東京",    30),
            ("東京",    "千葉",    40), ("千葉",    "東京",    40),
            ("東京",    "さいたま",  25), ("さいたま",  "東京",    25),
            ("横浜",    "海老名",   20), ("海老名",   "横浜",    20),
            ("海老名",   "厚木",    10), ("厚木",    "海老名",   10),
            ("厚木",    "八王子",   30), ("八王子",   "厚木",    30),
            ("八王子",   "東京",    40), ("東京",    "八王子",   40),
            ("さいたま",  "川越",    20), ("川越",    "さいたま",  20),
            ("川越",    "鶴ヶ島",   10), ("鶴ヶ島",   "川越",    10),
            ("鶴ヶ島",   "高崎",    60), ("高崎",    "鶴ヶ島",   60),
            ("高崎",    "宇都宮",   80), ("宇都宮",   "高崎",    80),
            ("宇都宮",   "さいたま",  90), ("さいたま",  "宇都宮",   90),
            ("千葉",    "成田",    40), ("成田",    "千葉",    40),
            ("成田",    "つくば",   50), ("つくば",   "成田",    50),
            ("つくば",   "東京",    60), ("東京",    "つくば",   60),
            ("厚木",    "御殿場",   50), ("御殿場",   "厚木",    50),
            ("八王子",   "甲府",    70), ("甲府",    "八王子",   70),
            ("川越",    "八王子",   30), ("八王子",   "川越",    30),
            ("海老名",   "八王子",   25), ("八王子",   "海老名",   25),
            ("つくば",   "宇都宮",   70), ("宇都宮",   "つくば",   70),
            ("高崎",    "長野",    100), ("長野",    "高崎",    100),
            ("御殿場",   "静岡",    60), ("静岡",    "御殿場",   60),
        ],
        "highlight": "御殿場を停止 → 静岡が完全孤立（他に八王子→甲府、高崎→長野も同構造）",
        "demo_failed_nodes": ["御殿場"],
    },
    "シナリオ3: 関東主要物流ネットワーク — 幹線遮断と迂回コスト": {
        "description": (
            "東京↔横浜 の直通ルート（30km）が自然災害等で**両方向同時に遮断**された場合、"
            "配送は 東京→八王子→海老名→横浜（85km）に迂回せざるを得ず、"
            "コストが**+55km（約2.8倍）** に膨れ上がる。"
            "接続は維持されるが迂回コストの増大を定量的に確認できる例。"
        ),
        "recommend_mode": "障害シミュレーション（影響範囲の確認）",
        "nodes": [
            "東京", "横浜", "千葉", "さいたま", "八王子", "海老名",
            "厚木", "川越", "鶴ヶ島", "高崎", "宇都宮", "成田",
            "つくば", "御殿場", "甲府", "長野", "静岡",
        ],
        "edges": [
            ("東京",    "横浜",    30), ("横浜",    "東京",    30),
            ("東京",    "千葉",    40), ("千葉",    "東京",    40),
            ("東京",    "さいたま",  25), ("さいたま",  "東京",    25),
            ("横浜",    "海老名",   20), ("海老名",   "横浜",    20),
            ("海老名",   "厚木",    10), ("厚木",    "海老名",   10),
            ("厚木",    "八王子",   30), ("八王子",   "厚木",    30),
            ("八王子",   "東京",    40), ("東京",    "八王子",   40),
            ("さいたま",  "川越",    20), ("川越",    "さいたま",  20),
            ("川越",    "鶴ヶ島",   10), ("鶴ヶ島",   "川越",    10),
            ("鶴ヶ島",   "高崎",    60), ("高崎",    "鶴ヶ島",   60),
            ("高崎",    "宇都宮",   80), ("宇都宮",   "高崎",    80),
            ("宇都宮",   "さいたま",  90), ("さいたま",  "宇都宮",   90),
            ("千葉",    "成田",    40), ("成田",    "千葉",    40),
            ("成田",    "つくば",   50), ("つくば",   "成田",    50),
            ("つくば",   "東京",    60), ("東京",    "つくば",   60),
            ("厚木",    "御殿場",   50), ("御殿場",   "厚木",    50),
            ("八王子",   "甲府",    70), ("甲府",    "八王子",   70),
            ("川越",    "八王子",   30), ("八王子",   "川越",    30),
            ("海老名",   "八王子",   25), ("八王子",   "海老名",   25),
            ("つくば",   "宇都宮",   70), ("宇都宮",   "つくば",   70),
            ("高崎",    "長野",    100), ("長野",    "高崎",    100),
            ("御殿場",   "静岡",    60), ("静岡",    "御殿場",   60),
        ],
        "highlight": "東京↔横浜 を遮断 → 迂回コスト 30km → 85km（+55km）に増大",
        "demo_failed_edges": [("東京", "横浜"), ("横浜", "東京")],
    },
}


# ---------------------------------------------------------------------------
# 自然順ソート（数字部分を数値として比較: N2 < N10）
# ---------------------------------------------------------------------------
def _natural_key(s: str) -> list:
    return [int(c) if c.isdigit() else c.lower()
            for c in re.split(r"(\d+)", str(s))]


# ---------------------------------------------------------------------------
# アルゴリズム: 安定SCCマップ生成
# ---------------------------------------------------------------------------
def build_stable_scc_map(G: nx.DiGraph) -> tuple:
    """
    強連結成分のインデックスを「最小ノード名の昇順」で安定化させる。
    nx.strongly_connected_components() は呼び出しごとに順序が変わる可能性があるため、
    描画と凡例で別々に enumerate() すると色ズレが生じる。
    本関数の返り値を描画・凡例の両方で共有することで色を一致させる。

    Returns:
      scc_map    : {node: scc_index}  サイズ1のSCCは -1
      large_sccs : サイズ2以上のSCCをmin(scc)昇順に並べたリスト
    """
    sccs = list(nx.strongly_connected_components(G))
    large_sccs = sorted(
        [s for s in sccs if len(s) > 1],
        key=lambda s: str(min(s, key=str))
    )
    scc_map: dict = {}
    for i, s in enumerate(large_sccs):
        for n in s:
            scc_map[n] = i
    for s in sccs:
        if len(s) == 1:
            for n in s:
                scc_map[n] = -1
    return scc_map, large_sccs


# ---------------------------------------------------------------------------
# アルゴリズム: 強橋検出 O(E × (V+E))
# ---------------------------------------------------------------------------
def find_strong_bridges(G: nx.DiGraph) -> list:
    """
    有向グラフの強橋を検出する。

    強橋の定義: 辺(u,v)を除去すると u→v の到達可能性が失われる辺。
    計算量: O(E × (V+E))

    実装上の注意:
      list(G.edges()) でスナップショットを取ってからループする。
      ループ中に G.remove_edge/add_edge を呼ぶため、スナップショットなしでは
      RuntimeError: dictionary changed size during iteration が発生する。
    """
    if len(G) <= 1:
        return []

    bridges: list = []
    sccs = list(nx.strongly_connected_components(G))
    node_to_scc: dict = {}
    for i, comp in enumerate(sccs):
        for n in comp:
            node_to_scc[n] = i

    for u, v in list(G.edges()):
        if node_to_scc[u] != node_to_scc[v]:
            continue
        G.remove_edge(u, v)
        if not nx.has_path(G, u, v):
            bridges.append((u, v))
        G.add_edge(u, v)

    return bridges


# ---------------------------------------------------------------------------
# アルゴリズム: カスケード故障検出
# ---------------------------------------------------------------------------
def find_cascade_failures(G_after: nx.DiGraph, direct_isolated: set) -> set:
    """
    直接孤立ノードの影響が伝播して実質到達不能になるノードを検出する。

    単純な入次数0判定では見逃す「連鎖的な補給不能」を捕捉する。
    例: A→B→C で A が孤立すると B は入次数>0でも補給不能になる。

    計算量: O(V × (V+E))
    """
    cascade_victims: set = set()
    direct_isolated = set(direct_isolated)

    for node in G_after.nodes():
        if node in direct_isolated:
            continue
        predecessors = list(nx.ancestors(G_after, node))
        if not predecessors:
            continue
        if all(p in direct_isolated for p in predecessors):
            cascade_victims.add(node)

    return cascade_victims


# ---------------------------------------------------------------------------
# アルゴリズム: 迂回コスト分析
# ---------------------------------------------------------------------------
def analyze_rerouting_cost(
    G: nx.DiGraph,
    G_after: nx.DiGraph,
    failed_edges: list,
) -> pd.DataFrame:
    """
    障害前後の最短経路コスト変化を計算する。
    weight 属性がない辺はすべて 1.0 として扱う。
    """
    results = []
    for u, v in failed_edges:
        try:
            cost_before = nx.shortest_path_length(G, u, v, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            cost_before = float("inf")
        try:
            cost_after = nx.shortest_path_length(G_after, u, v, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            cost_after = float("inf")

        if cost_after == float("inf"):
            status, delta = "到達不能（迂回なし）", "—"
        else:
            status = f"迂回可能（+{cost_after - cost_before:.1f}）"
            delta  = f"{cost_before:.1f} → {cost_after:.1f}"

        results.append({
            "ルート":       f"{u} → {v}",
            "障害前コスト": f"{cost_before:.1f}" if cost_before != float("inf") else "∞",
            "障害後コスト": f"{cost_after:.1f}"  if cost_after  != float("inf") else "∞",
            "変化":         delta,
            "状態":         status,
        })
    return pd.DataFrame(results) if results else pd.DataFrame()


# ---------------------------------------------------------------------------
# アルゴリズム: 障害シミュレーション
# ---------------------------------------------------------------------------
def simulate_failure(
    G: nx.DiGraph,
    failed_nodes: list | None = None,
    failed_edges: list | None = None,
) -> tuple:
    failed_nodes = failed_nodes or []
    failed_edges = failed_edges or []

    scc_before = {
        frozenset(s): i
        for i, s in enumerate(nx.strongly_connected_components(G))
        if len(s) > 1
    }

    G_after = G.copy()
    G_after.remove_nodes_from(failed_nodes)
    G_after.remove_edges_from(
        [e for e in failed_edges if G_after.has_edge(*e)]
    )

    isolated_complete, isolated_no_input, isolated_no_output = [], [], []
    for n in G_after.nodes():
        in_deg, out_deg = G_after.in_degree(n), G_after.out_degree(n)
        if   in_deg == 0 and out_deg == 0: isolated_complete.append(n)
        elif in_deg == 0:                  isolated_no_input.append(n)
        elif out_deg == 0:                 isolated_no_output.append(n)

    isolated_all     = isolated_complete + isolated_no_input + isolated_no_output
    cascade_failures = find_cascade_failures(G_after, set(isolated_all)) - set(isolated_all)

    scc_after_list = list(nx.strongly_connected_components(G_after))
    scc_after = {frozenset(s): i for i, s in enumerate(scc_after_list) if len(s) > 1}

    broken_sccs = []
    for old_scc in scc_before:
        surviving = old_scc - set(failed_nodes)
        if len(surviving) < 2:
            continue
        after_groups: dict = {}
        for n in surviving:
            for s in scc_after_list:
                if n in s:
                    after_groups.setdefault(frozenset(s), set()).add(n)
                    break
            else:
                after_groups.setdefault(frozenset({n}), set()).add(n)
        if len(after_groups) > 1:
            broken_sccs.append({"original": old_scc, "after": list(after_groups.keys())})

    return (
        G_after, isolated_all, isolated_complete,
        isolated_no_input, isolated_no_output,
        cascade_failures, scc_before, scc_after, broken_sccs,
    )


# ---------------------------------------------------------------------------
# 描画: Matplotlib（<=80ノード向け静止画）
# ---------------------------------------------------------------------------
def draw_network_matplotlib(
    G: nx.DiGraph, pos: dict, ax,
    bridge_edges=None, failed_nodes=None, failed_edges=None,
    isolated_nodes=None, cascade_nodes=None, scc_map=None, title="",
) -> None:
    bridge_edges   = set(map(tuple, bridge_edges   or []))
    failed_nodes   = set(failed_nodes  or [])
    failed_edges   = set(map(tuple, failed_edges   or []))
    isolated_nodes = set(isolated_nodes or [])
    cascade_nodes  = set(cascade_nodes  or [])

    normal_nodes  = [n for n in G.nodes()
                     if n not in failed_nodes and n not in isolated_nodes
                     and n not in cascade_nodes]
    isolated_draw = [n for n in G.nodes() if n in isolated_nodes]
    cascade_draw  = [n for n in G.nodes() if n in cascade_nodes]

    cmap = plt.colormaps["tab10"]
    if scc_map:
        node_colors = [
            cmap(scc_map.get(n, -1) % 10) if scc_map.get(n, -1) != -1 else "#cccccc"
            for n in normal_nodes
        ]
    else:
        node_colors = ["#4A90D9"] * len(normal_nodes)

    nx.draw_networkx_nodes(G, pos, nodelist=normal_nodes,
                           node_color=node_colors, node_size=600, ax=ax)
    if isolated_draw:
        nx.draw_networkx_nodes(G, pos, nodelist=isolated_draw,
                               node_color="#aaaaaa", node_size=600, node_shape="x", ax=ax)
    if cascade_draw:
        nx.draw_networkx_nodes(G, pos, nodelist=cascade_draw,
                               node_color="#f39c12", node_size=600, node_shape="d", ax=ax)

    # ノードラベルの描画（日本語フォント対応）
    # NetworkXはrcParamsを無視する場合があるため、明示的にfont_familyを指定
    current_font = matplotlib.rcParams.get('font.family', ['sans-serif'])
    if isinstance(current_font, list):
        current_font = current_font[0]
    
    nx.draw_networkx_labels(G, pos, labels={n: str(n) for n in G.nodes()},
                            font_color="white", font_weight="bold", font_size=8,
                            font_family=current_font, ax=ax)

    normal_edges = [e for e in G.edges() if e not in bridge_edges and e not in failed_edges]
    bridge_draw  = [e for e in G.edges() if e in bridge_edges]
    failed_draw  = [e for e in G.edges() if e in failed_edges]

    nx.draw_networkx_edges(G, pos, edgelist=normal_edges,
                           edge_color="#555555", arrowsize=12, arrowstyle="->", ax=ax)
    if bridge_draw:
        nx.draw_networkx_edges(G, pos, edgelist=bridge_draw,
                               edge_color="#e74c3c", width=2.5, arrowsize=14,
                               arrowstyle="->", ax=ax)
    if failed_draw:
        nx.draw_networkx_edges(G, pos, edgelist=failed_draw,
                               edge_color="#e74c3c", width=2, style="dashed",
                               arrowsize=12, arrowstyle="->", ax=ax)

    ax.set_title(title, fontsize=11, pad=10)
    ax.axis("off")


# ---------------------------------------------------------------------------
# 描画: PyVis（81〜500ノード向けインタラクティブ）
# ---------------------------------------------------------------------------
def draw_network_pyvis(
    G: nx.DiGraph, bridge_edges=None, failed_nodes=None,
    isolated_nodes=None, cascade_nodes=None, height="600px",
) -> None:
    try:
        from pyvis.network import Network
        import streamlit.components.v1 as components
    except ImportError:
        st.warning("PyVisがインストールされていません。`pip install pyvis` を実行してください。")
        return

    bridge_edges   = set(map(tuple, bridge_edges   or []))
    failed_nodes   = set(str(n) for n in (failed_nodes   or []))
    isolated_nodes = set(str(n) for n in (isolated_nodes or []))
    cascade_nodes  = set(str(n) for n in (cascade_nodes  or []))

    net = Network(height=height, width="100%", directed=True,
                  bgcolor="#1a1a2e", font_color="white")
    net.barnes_hut(gravity=-5000, central_gravity=0.3, spring_length=100)

    for node in G.nodes():
        ns = str(node)
        if   ns in failed_nodes:   color, shape, tip = "#e74c3c", "diamond",  "停止中の拠点"
        elif ns in isolated_nodes: color, shape, tip = "#aaaaaa", "square",   "孤立拠点（障害影響）"
        elif ns in cascade_nodes:  color, shape, tip = "#f39c12", "triangle", "カスケード故障拠点"
        else:                      color, shape, tip = "#4A90D9", "dot",      "正常拠点"
        net.add_node(ns, label=ns, color=color, shape=shape, size=15, title=tip)

    for u, v in G.edges():
        if (u, v) in bridge_edges:
            net.add_edge(str(u), str(v), color="#e74c3c", width=3, title="強橋（単一障害点）")
        else:
            net.add_edge(str(u), str(v), color="#888888", width=1)

    components.html(net.generate_html(), height=int(height.replace("px", "")))


# ---------------------------------------------------------------------------
# CSV読み込み（キャッシュ付き）
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="CSVを読み込み中...")
def load_graph_from_csv(file_bytes: bytes) -> tuple:
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as e:
        return None, f"CSV読み込みエラー: {e}"

    if "from" not in df.columns or "to" not in df.columns:
        return None, "'from' と 'to' 列が必要です。"

    G = nx.DiGraph()
    for _, row in df.iterrows():
        w = 1.0
        if "cost" in df.columns and pd.notna(row.get("cost")):
            try:
                w = float(row["cost"])
            except (ValueError, TypeError):
                pass
        G.add_edge(str(row["from"]).strip(), str(row["to"]).strip(), weight=w)
    return G, None


# ===========================================================================
# ページ本体
# ===========================================================================

# ---------------------------------------------------------------------------
# ヘッダー: 常時表示（5秒で価値が伝わる3行）
# ---------------------------------------------------------------------------
st.title("🚚 物流ネットワーク障害シミュレーター")
st.markdown(
    "物流・交通・通信ネットワークでは、**たった1本のルートが止まるだけで広範囲の配送が麻痺する**ことがある。  \n"
    "このツールは「どのルートが止まると致命的か（強橋）」を事前に特定し、  \n"
    "障害発生時の**直接影響・連鎖影響（カスケード故障）・迂回コスト**をリアルタイムで可視化する。"
)

# ---------------------------------------------------------------------------
# 説明セクション: expander（興味ある人だけ開く）
# ---------------------------------------------------------------------------
with st.expander("📖 詳細説明・用語定義・想定ユースケース（クリックで展開）"):
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### 🔑 主要用語")
        st.markdown("""
**強橋（Strong Bridge）**
: 有向グラフにおいて、その辺を除去すると起点から終点への到達可能性が失われる辺。
物流文脈では「この1本が止まると循環配送が崩れる」ルートに相当する。

**強連結成分（SCC: Strongly Connected Component）**
: グラフ内で互いに到達可能なノードの最大集合。
物流文脈では「この拠点群の間は相互に配送が回っている」ブロック。

**カスケード故障（Cascade Failure）**
: 直接障害を受けていないノードが、補給元の孤立によって連鎖的に到達不能になる現象。
入次数の確認だけでは見逃すため、祖先ノードの到達可能性を追跡して検出する。
        """)

    with col_r:
        st.markdown("#### 🏭 想定ユースケース")
        st.markdown("""
| 分野 | 活用場面 |
|------|---------|
| 物流・配送 | 幹線ルートの冗長化計画、災害時の代替ルート事前評価 |
| 交通インフラ | 道路・鉄道ネットワークの脆弱区間特定 |
| 通信ネットワーク | バックボーン回線の単一障害点洗い出し |
| サプライチェーン | 特定サプライヤー停止時の影響範囲シミュレーション |

#### ⚙️ アルゴリズム計算量
| 処理 | 計算量 |
|------|--------|
| 強橋検出 | O(E × (V+E)) |
| カスケード故障検出 | O(V × (V+E)) |
| 迂回コスト分析 | O(V × E) |

描画: ≤80ノード → Matplotlib静止画 / 81〜500 → PyVisインタラクティブ
        """)

st.divider()

# ---------------------------------------------------------------------------
# サイドバー: デモシナリオ（最上部に配置）
# ---------------------------------------------------------------------------
st.sidebar.header("🎬 デモシナリオ")
st.sidebar.caption("ボタン1つで課題設定済みのネットワークを読み込めます")

for scenario_name, scenario in DEMO_SCENARIOS.items():
    if st.sidebar.button(scenario_name, use_container_width=True):
        G_demo = nx.DiGraph()
        for node in scenario["nodes"]:
            G_demo.add_node(node)
        for u, v, w in scenario["edges"]:
            G_demo.add_edge(u, v, weight=float(w))
        st.session_state["demo_graph"]        = G_demo
        st.session_state["active_scenario"]   = scenario_name
        st.session_state["demo_failed_nodes"] = scenario.get("demo_failed_nodes", [])
        st.session_state["demo_failed_edges"] = scenario.get("demo_failed_edges", [])
        st.session_state["_prev_graph_key"]   = ""  # ランダム生成キャッシュをリセット

st.sidebar.divider()

# ---------------------------------------------------------------------------
# サイドバー: ネットワーク入力
# ---------------------------------------------------------------------------
st.sidebar.header("📦 ネットワーク入力")
input_method = st.sidebar.radio(
    "入力方法",
    ["テキスト入力", "ランダム生成", "CSVアップロード"],
    help="デモシナリオを読み込んだ場合、この設定は上書きされます"
)

DRAW_LIMIT_STATIC      = 80
DRAW_LIMIT_INTERACTIVE = 500

G            = None
preview_ready = False

# デモシナリオが読み込まれている場合はそちらを優先
if "demo_graph" in st.session_state:
    G             = st.session_state["demo_graph"]
    preview_ready = True

    active        = st.session_state.get("active_scenario", "")
    scenario_data = DEMO_SCENARIOS.get(active, {})

    st.info(
        f"**📌 {active}**  \n"
        f"{scenario_data.get('description', '')}  \n\n"
        f"💡 **注目ポイント**: {scenario_data.get('highlight', '')}"
    )
    st.sidebar.success(
        f"✅ デモ読み込み済み  \n"
        f"{G.number_of_nodes()}拠点 / {G.number_of_edges()}ルート"
    )
    if st.sidebar.button("❌ デモをクリアして手動入力に戻る"):
        del st.session_state["demo_graph"]
        del st.session_state["active_scenario"]
        st.session_state.pop("demo_failed_nodes", None)
        st.session_state.pop("demo_failed_edges", None)
        st.rerun()

elif input_method == "テキスト入力":
    st.sidebar.markdown("**ルート形式**: `from,to` または `from,to,cost`")
    nodes_raw = st.sidebar.text_input(
        "拠点 (カンマ区切り)",
        "A,B,C,D,E,F,G,H,I,J"
    )
    edges_raw = st.sidebar.text_area(
        "ルート (1行ずつ)",
        "A,B,1\nB,C,2\nC,A,1\nC,D,5\nD,E,1\nE,F,2\nF,D,1\nF,G,3\nG,H,1\nH,I,2\nI,J,1\nJ,G,2"
    )
    try:
        G = nx.DiGraph()
        nodes = [n.strip() for n in nodes_raw.split(",") if n.strip()]
        if not nodes:
            st.sidebar.error("拠点を1つ以上入力してください。")
        else:
            G.add_nodes_from(nodes)
            for line in edges_raw.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) == 3 and all(parts):
                    try:    G.add_edge(parts[0], parts[1], weight=float(parts[2]))
                    except ValueError: G.add_edge(parts[0], parts[1], weight=1.0)
                elif len(parts) == 2 and all(parts):
                    G.add_edge(parts[0], parts[1], weight=1.0)
                elif line.strip():
                    st.sidebar.warning(f"スキップ: '{line}'")
            preview_ready = True
    except Exception as e:
        st.sidebar.error(f"入力エラー: {e}")

elif input_method == "ランダム生成":
    st.sidebar.markdown(
        "⚠️ **パフォーマンス目安**\n"
        "- ~80ノード: 静止画描画\n"
        "- ~500ノード: インタラクティブ描画\n"
        "- 500超: 描画スキップ（数値のみ）"
    )
    n_nodes   = st.sidebar.number_input("拠点数", min_value=2, max_value=200, value=15)
    edge_prob = st.sidebar.slider("ルート密度（接続確率）", 0.0, 1.0, 0.15)
    gen_seed  = st.sidebar.number_input("シード（固定再現）", value=42)
    graph_key = f"rand_{int(n_nodes)}_{edge_prob:.3f}_{int(gen_seed)}"

    _prev_key = st.session_state.get("_prev_graph_key", "")
    if graph_key != _prev_key or "current_graph" not in st.session_state:
        raw = nx.fast_gnp_random_graph(int(n_nodes), edge_prob,
                                       seed=int(gen_seed), directed=True)
        mapping = {i: f"N{i}" for i in raw.nodes()}
        st.session_state["current_graph"] = nx.relabel_nodes(raw, mapping)
        for u, v in st.session_state["current_graph"].edges():
            st.session_state["current_graph"][u][v]["weight"] = float(_rnd.randint(1, 5))
        st.session_state["_prev_graph_key"] = graph_key

    if st.sidebar.button("🎲 別の乱数で再生成"):
        new_seed = _rnd.randint(0, 9999)
        raw = nx.fast_gnp_random_graph(int(n_nodes), edge_prob,
                                       seed=new_seed, directed=True)
        mapping = {i: f"N{i}" for i in raw.nodes()}
        st.session_state["current_graph"] = nx.relabel_nodes(raw, mapping)
        for u, v in st.session_state["current_graph"].edges():
            st.session_state["current_graph"][u][v]["weight"] = float(_rnd.randint(1, 5))
        st.sidebar.caption(f"使用シード: {new_seed}")

    G = st.session_state.get("current_graph")
    preview_ready = G is not None

elif input_method == "CSVアップロード":
    st.sidebar.markdown(
        "**CSVフォーマット**\n"
        "- 必須列: `from`, `to`\n"
        "- 任意列: `cost`（迂回コスト分析に使用）"
    )
    uploaded = st.sidebar.file_uploader("CSVファイルを選択", type=["csv"])
    if uploaded:
        file_bytes = uploaded.getvalue()
        G, err = load_graph_from_csv(file_bytes)
        if err:
            st.sidebar.error(err)
        else:
            st.sidebar.success(f"✅ {G.number_of_nodes()}拠点 / {G.number_of_edges()}ルート")
            preview_ready = True


# ===========================================================================
# メイン: 分析モード
# ===========================================================================
if G and preview_ready:
    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()

    st.sidebar.divider()
    st.sidebar.header("🔍 分析モード")

    # デモシナリオで推奨モードが設定されている場合はデフォルトを変える
    active_scenario = st.session_state.get("active_scenario", "")
    recommend_mode  = DEMO_SCENARIOS.get(active_scenario, {}).get(
        "recommend_mode", "強橋分析（単一障害点の特定）"
    )
    mode_options  = ["強橋分析（単一障害点の特定）", "障害シミュレーション（影響範囲の確認）"]
    default_index = mode_options.index(recommend_mode)
    mode = st.sidebar.radio("モードを選択", mode_options, index=default_index)

    # =========================================================================
    # モード1: 強橋分析
    # =========================================================================
    if mode == "強橋分析（単一障害点の特定）":
        st.subheader("🔴 強橋分析 — 単一障害点となるルートの特定")
        st.markdown(
            "**強橋**とは、そのルートが1本でも止まると循環配送（強連結性）が崩れる辺。"
            " 赤く表示されたルートが単一障害点です。"
        )

        with st.spinner("強橋を検出中..."):
            bridges = find_strong_bridges(G)

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("拠点数", node_count)
        col_b.metric("ルート数", edge_count)
        col_c.metric("強橋（単一障害点）数", len(bridges),
                     delta=f"全ルートの {len(bridges) / max(edge_count, 1) * 100:.1f}%",
                     delta_color="inverse")

        if bridges:
            st.warning(f"⚠️ {len(bridges)} 本の強橋が検出されました。これらのルートが止まると循環配送が崩れます。")
            df_bridges = pd.DataFrame(bridges, columns=["出発拠点", "到着拠点"])
            df_bridges.index += 1
            st.dataframe(df_bridges, use_container_width=True)
        else:
            st.success("✅ 強橋は検出されませんでした。全ルートに冗長性があります。")

        if node_count <= DRAW_LIMIT_STATIC:
            fig, ax = plt.subplots(figsize=(12, 7))
            pos = nx.spring_layout(G, seed=42, k=1.5 / max(node_count ** 0.5, 1))
            scc_map, large_sccs = build_stable_scc_map(G)
            draw_network_matplotlib(G, pos, ax, bridge_edges=bridges, scc_map=scc_map,
                                    title="物流ネットワーク — 赤: 強橋 / 色: 強連結成分")
            cmap = plt.colormaps["tab10"]
            legend_elements = [mpatches.Patch(color="#e74c3c", label="強橋（単一障害点）")]
            for i in range(min(len(large_sccs), 5)):
                legend_elements.append(mpatches.Patch(color=cmap(i % 10), label=f"強連結成分 {i + 1}"))
            if len(large_sccs) > 5:
                legend_elements.append(
                    mpatches.Patch(color="white", label=f"... 他 {len(large_sccs) - 5} 個"))
            legend_elements += [mpatches.Patch(color="#cccccc", label="非強連結（サイズ1）")]
            ax.legend(handles=legend_elements, loc="lower left", fontsize=9)
            st.pyplot(fig)

        elif node_count <= DRAW_LIMIT_INTERACTIVE:
            st.info("💡 ノード数が多いためインタラクティブ表示に切り替えました。ズーム・ドラッグが可能です。")
            draw_network_pyvis(G, bridge_edges=bridges)

        else:
            st.info(f"拠点数が {DRAW_LIMIT_INTERACTIVE} を超えているため描画をスキップしました（{node_count}拠点）。")

    # =========================================================================
    # モード2: 障害シミュレーション
    # =========================================================================
    elif mode == "障害シミュレーション（影響範囲の確認）":
        st.subheader("🛑 障害シミュレーション — 拠点・ルート停止時の影響範囲")

        st.sidebar.divider()
        st.sidebar.subheader("障害設定")

        all_nodes = sorted(G.nodes(), key=_natural_key)
        all_edges_str = sorted(
            [f"{u} → {v}" for u, v in G.edges()],
            key=lambda e: (_natural_key(e.split(" → ")[0]), _natural_key(e.split(" → ")[1]))
        )

        # デモシナリオで障害拠点が設定されている場合はデフォルト選択
        demo_failed = st.session_state.get("demo_failed_nodes", [])
        failed_nodes_raw = st.sidebar.multiselect(
            "停止する拠点（複数選択可）",
            options=all_nodes,
            default=[n for n in demo_failed if n in all_nodes],
        )
        demo_failed_edges_str = [
            f"{u} → {v}"
            for u, v in st.session_state.get("demo_failed_edges", [])
        ]
        failed_edges_raw = st.sidebar.multiselect(
            "停止するルート（複数選択可）",
            options=all_edges_str,
            default=[e for e in demo_failed_edges_str if e in all_edges_str],
        )
        failed_edges = [tuple(e.replace(" ", "").split("→")) for e in failed_edges_raw]

        if not failed_nodes_raw and not failed_edges:
            st.info("⬅️ サイドバーから停止させる拠点またはルートを選択してください。")
            if node_count <= DRAW_LIMIT_STATIC:
                fig, ax = plt.subplots(figsize=(12, 7))
                pos = nx.spring_layout(G, seed=42, k=1.5 / max(node_count ** 0.5, 1))
                bridges = find_strong_bridges(G)
                scc_map, _ = build_stable_scc_map(G)
                draw_network_matplotlib(G, pos, ax, bridge_edges=bridges,
                                        scc_map=scc_map, title="現状ネットワーク（赤: 強橋）")
                st.pyplot(fig)
            elif node_count <= DRAW_LIMIT_INTERACTIVE:
                bridges = find_strong_bridges(G)
                draw_network_pyvis(G, bridge_edges=bridges)

        else:
            with st.spinner("障害シミュレーション実行中..."):
                (G_after, isolated_all, isolated_complete,
                 isolated_no_input, isolated_no_output,
                 cascade_failures, scc_before, scc_after, broken_sccs) = simulate_failure(
                    G, failed_nodes=failed_nodes_raw, failed_edges=failed_edges,
                )

            col_a, col_b, col_c, col_d, col_e = st.columns(5)
            col_a.metric("停止拠点数",          len(failed_nodes_raw))
            col_b.metric("停止ルート数",          len(failed_edges))
            col_c.metric("直接孤立拠点数",        len(isolated_all),
                         delta=f"+{len(isolated_all)}" if isolated_all else "0",
                         delta_color="inverse")
            col_d.metric("カスケード故障数",      len(cascade_failures),
                         delta=f"+{len(cascade_failures)}" if cascade_failures else "0",
                         delta_color="inverse")
            col_e.metric("分裂した循環ルート数",  len(broken_sccs),
                         delta=f"+{len(broken_sccs)}" if broken_sccs else "0",
                         delta_color="inverse")

            if isolated_complete:
                st.error(
                    f"🚫 **完全孤立拠点（{len(isolated_complete)}箇所）**: "
                    + "、".join(str(n) for n in sorted(isolated_complete, key=str))
                    + "\n\nこれらの拠点は配送の送受信が完全に不能です。"
                )
            if isolated_no_input:
                st.warning(
                    f"📥 **補給不能拠点（{len(isolated_no_input)}箇所）**: "
                    + "、".join(str(n) for n in sorted(isolated_no_input, key=str))
                    + "\n\nこれらの拠点には荷物が届きません（出荷のみ可能）。"
                )
            if isolated_no_output:
                st.warning(
                    f"📤 **配送不能拠点（{len(isolated_no_output)}箇所）**: "
                    + "、".join(str(n) for n in sorted(isolated_no_output, key=str))
                    + "\n\nこれらの拠点からは荷物が出せません（受取のみ可能）。"
                )
            if cascade_failures:
                st.warning(
                    f"🔗 **カスケード故障（連鎖孤立）{len(cascade_failures)}箇所**: "
                    + "、".join(str(n) for n in sorted(cascade_failures, key=str))
                    + "\n\n直接障害ではなく、供給元の孤立が伝播して実質到達不能になった拠点です。"
                )
            if broken_sccs:
                st.warning(f"⚠️ **{len(broken_sccs)}個の循環配送ルートが分裂しました**")
                for i, item in enumerate(broken_sccs):
                    with st.expander(f"分裂した循環ルート {i+1}（元: {len(item['original'])}拠点）"):
                        st.write("**元の強連結成分:**")
                        st.code(sorted(item["original"], key=str))
                        st.write("**障害後の分裂結果:**")
                        for j, group in enumerate(item["after"]):
                            label = "循環維持" if len(group) > 1 else "孤立"
                            st.write(f"グループ {j+1} ({label}): {sorted(group, key=str)}")

            if failed_edges:
                st.divider()
                st.subheader("🔄 迂回コスト分析")
                st.caption("障害前後の最短経路コストを比較します。")
                df_cost = analyze_rerouting_cost(G, G_after, failed_edges)
                if not df_cost.empty:
                    st.dataframe(df_cost, use_container_width=True)

            if not isolated_all and not broken_sccs and not cascade_failures:
                st.success("✅ 指定した障害範囲では循環配送への影響はありませんでした。")

            if node_count <= DRAW_LIMIT_STATIC:
                bridges_before = find_strong_bridges(G)
                scc_map_before, large_sccs_before = build_stable_scc_map(G)
                scc_map_after,  large_sccs_after  = build_stable_scc_map(G_after)

                pos = nx.spring_layout(G, seed=42, k=1.5 / max(node_count ** 0.5, 1))
                pos_after = {n: p for n, p in pos.items() if n in G_after.nodes()}

                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
                draw_network_matplotlib(G, pos, ax1,
                                        bridge_edges=bridges_before,
                                        failed_nodes=failed_nodes_raw,
                                        failed_edges=failed_edges,
                                        scc_map=scc_map_before,
                                        title="障害前（赤辺: 強橋 / 赤点線: 停止ルート）")
                draw_network_matplotlib(G_after, pos_after, ax2,
                                        isolated_nodes=isolated_all,
                                        cascade_nodes=list(cascade_failures),
                                        scc_map=scc_map_after,
                                        title="障害後（灰×: 孤立 / 橙◆: カスケード故障 / 色: 強連結成分）")

                cmap = plt.colormaps["tab10"]
                num_sccs = max(len(large_sccs_before), len(large_sccs_after))
                legend_elements = [mpatches.Patch(color="#e74c3c", label="強橋 / 停止対象")]
                for i in range(min(num_sccs, 4)):
                    legend_elements.append(mpatches.Patch(color=cmap(i % 10), label=f"強連結成分 {i+1}"))
                if num_sccs > 4:
                    legend_elements.append(mpatches.Patch(color="white", label="... 他"))
                legend_elements += [
                    mpatches.Patch(color="#cccccc", label="非強連結（サイズ1）"),
                    mpatches.Patch(color="#aaaaaa", label="孤立拠点（障害）"),
                    mpatches.Patch(color="#f39c12", label="カスケード故障拠点"),
                ]
                fig.legend(handles=legend_elements, loc="lower center",
                           ncol=min(len(legend_elements), 7), fontsize=9,
                           bbox_to_anchor=(0.5, -0.02))
                plt.tight_layout()
                st.pyplot(fig)

            elif node_count <= DRAW_LIMIT_INTERACTIVE:
                st.info("💡 インタラクティブ表示（障害後）")
                draw_network_pyvis(G_after,
                                   failed_nodes=failed_nodes_raw,
                                   isolated_nodes=isolated_all,
                                   cascade_nodes=list(cascade_failures))
            else:
                st.info(
                    f"拠点数が {DRAW_LIMIT_INTERACTIVE} を超えているため描画をスキップしました（{node_count}拠点）。"
                )

# ---------------------------------------------------------------------------
# 初期画面: デモ未読み込み・入力なし
# ---------------------------------------------------------------------------
else:
    st.markdown("### 👈 まずはデモシナリオを試してみてください")
    st.markdown(
        "左サイドバーの **🎬 デモシナリオ** から3つのシナリオを選択できます。  \n"
        "ボタン1つでネットワークが読み込まれ、すぐに分析を開始できます。"
    )
    st.markdown("##### 関東17拠点ネットワーク（実在ベース）")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            "🗾 **シナリオ1: 末端依存の強橋**  \n"
            "長野・静岡・甲府への  \n"
            "単一ルート依存を可視化。"
        )
    with col2:
        st.markdown(
            "🏭 **シナリオ2: 中継拠点停止**  \n"
            "御殿場停止 → 静岡が  \n"
            "完全孤立する構造を確認。"
        )
    with col3:
        st.markdown(
            "🚧 **シナリオ3: 幹線遮断と迂回コスト**  \n"
            "東京↔横浜 遮断で  \n"
            "迂回コストが2.8倍に増大。"
        )