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

from algorithms import (
    find_strong_bridges,
    simulate_failure,         # 分析モード（後半）の障害シミュレーションで必要
    analyze_rerouting_cost,   # 分析モード（後半）の迂回コスト計算で必要
    build_stable_scc_map,     # 分析モード（後半）のMatplotlib描画で必要
    _natural_key
)
from scenarios import DEMO_SCENARIOS  # ← 【追加】サイドバーのデモ読み込みで必須
from visualization import (
    draw_network_pyvis,
    draw_network_matplotlib   # 分析モード（後半）の静止画描画で必要
)

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
    "障害発生時の**直接影響・連鎖影響・迂回コスト**をリアルタイムで可視化する。"
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
物流では「この1本が止まると循環配送が崩れる」ルートに相当する。

**強連結成分（SCC: Strongly Connected Component）**
: グラフ内で互いに到達可能なノードの最大集合。
物流では「この拠点群の間は相互に配送が回っている」ブロック。

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

描画: ≤80ノード → Matplotlib静止画 / 81〜200 → PyVisインタラクティブ
        """)

st.divider()

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
DRAW_LIMIT_INTERACTIVE = 200

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
        "- ~200ノード: インタラクティブ描画\n"
        "- 200超: 描画スキップ（数値のみ）"
    )
    n_nodes   = st.sidebar.number_input("拠点数", min_value=2, max_value=1000, value=15)
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