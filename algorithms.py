"""グラフアルゴリズムのコア部分（Streamlitに依存しない純粋なロジック）。

- 強橋の検出：支配木（dominator tree）を用いた手法
- カスケード故障の検出：多始点BFSによる O(V + E) の手法
- 迂回コストの分析：障害前後の最短経路コストの比較
- 障害シミュレーション：拠点・ルート停止後の孤立・連鎖・SCC分裂の判定
"""
from __future__ import annotations

import re
from collections import deque
from typing import NamedTuple

import networkx as nx
import pandas as pd

INF = float("inf")


# ---------------------------------------------------------------------------
# 自然順ソート（数字部分を数値として比較: N2 < N10）
# ---------------------------------------------------------------------------
def natural_key(s) -> list:
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", str(s))]


# ---------------------------------------------------------------------------
# 強連結成分マップ（描画と凡例で色を一致させるため順序を安定化）
# ---------------------------------------------------------------------------
def build_stable_scc_map(G: nx.DiGraph) -> tuple[dict, list]:
    """強連結成分のインデックスを「最小ノード名の昇順」で安定化させる。

    nx.strongly_connected_components() の列挙順は保証されないため、
    描画と凡例で別々に番号を振ると色がずれる。この関数の返り値を共有して防ぐ。

    Returns:
        scc_map:    {node: scc_index}。サイズ1のSCCは -1
        large_sccs: サイズ2以上のSCCを min(scc) の昇順に並べたリスト
    """
    sccs = list(nx.strongly_connected_components(G))
    large_sccs = sorted((s for s in sccs if len(s) > 1), key=lambda s: str(min(s, key=str)))
    scc_map = {n: -1 for n in G.nodes()}
    for i, s in enumerate(large_sccs):
        for n in s:
            scc_map[n] = i
    return scc_map, large_sccs


# ---------------------------------------------------------------------------
# 強橋の検出
# ---------------------------------------------------------------------------
def _flow_graph_bridges(H: nx.DiGraph, root) -> set:
    """フローグラフ H(root) の橋（root から到達するのに必ず通る辺）を求める。

    各辺 (u, v) の中点に補助ノード x を挟んだグラフで支配木を求めると、
    「辺 (u, v) が橋」⇔「x が v の直接支配節点」が成り立つ。
    """
    split = nx.DiGraph()
    split.add_nodes_from(H.nodes())
    for u, v in H.edges():
        x = ("__edge__", u, v)  # 元のノード名（文字列）と衝突しない補助ノード
        split.add_edge(u, x)
        split.add_edge(x, v)

    idom = nx.immediate_dominators(split, root)
    return {(u, v) for u, v in H.edges() if v != root and idom.get(v) == ("__edge__", u, v)}


def find_strong_bridges(G: nx.DiGraph) -> list[tuple]:
    """有向グラフの強橋を検出する。入力グラフは変更しない。

    強橋：除去すると強連結成分の数が増える辺。強連結な部分グラフ内の辺 (u, v) が
    強橋であることと、除去後に u から v へ到達できなくなることは同値。

    手法（Italiano, Laura, Santaroni 2012）：
        強連結な成分 C の任意の頂点 r について、
        強橋 ＝（C の r を始点とするフローグラフの橋）∪（逆グラフでの橋）
        各橋は支配木から求まるため、成分ごとに支配木を2回計算すればよい。
        Lengauer–Tarjan 法を使えば全体で線形時間になる。
        本実装では NetworkX の immediate_dominators（Cooper–Harvey–Kennedy法）を使用。
    """
    bridges: set = set()
    for comp in nx.strongly_connected_components(G):
        if len(comp) < 2:
            continue  # 成分をまたぐ辺はもともと循環に寄与しないため対象外
        H = G.subgraph(comp)
        root = min(comp, key=natural_key)
        bridges |= _flow_graph_bridges(H, root)
        bridges |= {(u, v) for v, u in _flow_graph_bridges(H.reverse(copy=False), root)}

    order = {e: i for i, e in enumerate(G.edges())}
    return sorted(bridges, key=order.__getitem__)


def find_strong_bridges_naive(G: nx.DiGraph) -> list[tuple]:
    """強橋の素朴な検出（辺を1本ずつ除いて到達可能性を調べる）。O(E × (V + E))。

    高速版の正しさを検証するための参照実装。グラフのコピー上で操作し、入力は変更しない。
    """
    H = nx.DiGraph(G.edges())
    node_to_scc = {}
    for i, comp in enumerate(nx.strongly_connected_components(H)):
        for n in comp:
            node_to_scc[n] = i

    bridges = []
    for u, v in G.edges():
        if node_to_scc[u] != node_to_scc[v]:
            continue
        H.remove_edge(u, v)
        if not nx.has_path(H, u, v):
            bridges.append((u, v))
        H.add_edge(u, v)
    return bridges


# ---------------------------------------------------------------------------
# カスケード故障の検出
# ---------------------------------------------------------------------------
def find_cascade_failures(G_after: nx.DiGraph, direct_isolated: set) -> set:
    """直接孤立ノードの影響が伝播して、実質的に補給を受けられなくなるノードを検出する。

    定義：直接孤立していないノード v のうち、祖先（v へ到達できるノード）が1つ以上あり、
    かつ祖先がすべて直接孤立ノードであるもの。
    例：X → A → B → C で X が停止すると、A は入次数0で直接孤立する。
    B は入次数>0だが、補給元が孤立した A だけなので補給不能（カスケード故障）になる。

    手法：直接孤立していないノードの後続ノードを始点に多始点BFSを行い、
    健全な補給元から到達できるノード集合 R を求める。R に含まれず、
    かつ入ってくる辺があるノードがカスケード故障である。O(V + E)。
    """
    direct_isolated = set(direct_isolated)
    reached: set = set()
    queue: deque = deque()

    for u in G_after.nodes():
        if u in direct_isolated:
            continue
        for v in G_after.successors(u):
            if v != u and v not in reached:  # 自己ループは「自分自身が補給元」とはみなさない
                reached.add(v)
                queue.append(v)

    while queue:
        u = queue.popleft()
        for v in G_after.successors(u):
            if v not in reached:
                reached.add(v)
                queue.append(v)

    return {
        v for v in G_after.nodes()
        if v not in direct_isolated
        and v not in reached
        and any(p != v for p in G_after.predecessors(v))
    }


# ---------------------------------------------------------------------------
# 迂回コストの分析
# ---------------------------------------------------------------------------
def _shortest_cost(G: nx.DiGraph, u, v) -> float:
    try:
        return nx.shortest_path_length(G, u, v, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return INF


def analyze_rerouting_cost(G: nx.DiGraph, G_after: nx.DiGraph, failed_edges: list) -> pd.DataFrame:
    """停止したルートの両端について、障害前後の最短経路コストを比較する。

    weight 属性がない辺のコストは 1 として扱う。
    """
    def fmt(c: float) -> str:
        return "∞" if c == INF else f"{c:.1f}"

    rows = []
    for u, v in failed_edges:
        before, after = _shortest_cost(G, u, v), _shortest_cost(G_after, u, v)
        if after == INF:
            status, change = "到達不能（迂回なし）", "—"
        else:
            status, change = f"迂回可能（+{after - before:.1f}）", f"{fmt(before)} → {fmt(after)}"
        rows.append({
            "ルート": f"{u} → {v}",
            "障害前コスト": fmt(before),
            "障害後コスト": fmt(after),
            "変化": change,
            "状態": status,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 障害シミュレーション
# ---------------------------------------------------------------------------
class FailureResult(NamedTuple):
    G_after: nx.DiGraph
    isolated_all: list         # 直接孤立した拠点（下の3種類の和）
    isolated_complete: list    # 入次数・出次数ともに0
    isolated_no_input: list    # 入次数0（補給不能）
    isolated_no_output: list   # 出次数0（配送不能）
    cascade_failures: set      # 連鎖的に補給不能になった拠点
    scc_before: dict           # 障害前のサイズ2以上のSCC
    scc_after: dict            # 障害後のサイズ2以上のSCC
    broken_sccs: list          # 分裂したSCC {"original": ..., "after": [...]}


def simulate_failure(G: nx.DiGraph, failed_nodes=None, failed_edges=None) -> FailureResult:
    """拠点・ルートの停止をシミュレーションし、影響範囲を返す。入力グラフは変更しない。"""
    failed_nodes = list(failed_nodes or [])
    failed_edges = list(failed_edges or [])

    scc_before = {
        frozenset(s): i for i, s in enumerate(nx.strongly_connected_components(G)) if len(s) > 1
    }

    G_after = G.copy()
    G_after.remove_nodes_from(failed_nodes)
    G_after.remove_edges_from([e for e in failed_edges if G_after.has_edge(*e)])

    isolated_complete, isolated_no_input, isolated_no_output = [], [], []
    for n in G_after.nodes():
        in_deg, out_deg = G_after.in_degree(n), G_after.out_degree(n)
        if in_deg == 0 and out_deg == 0:
            isolated_complete.append(n)
        elif in_deg == 0:
            isolated_no_input.append(n)
        elif out_deg == 0:
            isolated_no_output.append(n)

    isolated_all = isolated_complete + isolated_no_input + isolated_no_output
    cascade_failures = find_cascade_failures(G_after, set(isolated_all))

    after_list = list(nx.strongly_connected_components(G_after))
    scc_after = {frozenset(s): i for i, s in enumerate(after_list) if len(s) > 1}
    node_to_after = {n: frozenset(s) for s in after_list for n in s}

    broken_sccs = []
    for old_scc in scc_before:
        surviving = old_scc - set(failed_nodes)
        if len(surviving) < 2:
            continue
        groups = {node_to_after[n] for n in surviving}
        if len(groups) > 1:
            broken_sccs.append({"original": old_scc, "after": [g & surviving for g in groups]})

    return FailureResult(
        G_after, isolated_all, isolated_complete, isolated_no_input, isolated_no_output,
        cascade_failures, scc_before, scc_after, broken_sccs,
    )
