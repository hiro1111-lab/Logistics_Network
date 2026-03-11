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
import matplotlib

# ---------------------------------------------------------------------------
# 自作モジュール（分割したファイル）からのインポートを追加
# ---------------------------------------------------------------------------
from algorithms import (
    find_strong_bridges,
    build_stable_scc_map,
    simulate_failure,
    analyze_rerouting_cost,
    _natural_key  # もし _natural_key も algorithms.py に移動している場合
)
from scenarios import DEMO_SCENARIOS

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
# 描画: PyVis（81〜200ノード向けインタラクティブ）
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

