import re
import networkx as nx
import pandas as pd

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
