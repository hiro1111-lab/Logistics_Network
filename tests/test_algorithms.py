import random

import networkx as nx
import pytest

from algorithms import (
    analyze_rerouting_cost,
    find_cascade_failures,
    find_strong_bridges,
    find_strong_bridges_naive,
    simulate_failure,
)
from scenarios import DEMO_SCENARIOS, build_demo_graph

SCENARIO_NAMES = list(DEMO_SCENARIOS)


def random_digraph(n: int, p: float, seed: int, self_loops: bool = False) -> nx.DiGraph:
    G = nx.gnp_random_graph(n, p, seed=seed, directed=True)
    if self_loops:
        rng = random.Random(seed)
        G.add_edges_from((v, v) for v in G.nodes() if rng.random() < 0.1)
    return nx.relabel_nodes(G, {i: f"N{i}" for i in G.nodes()})


def cascade_failures_naive(G_after: nx.DiGraph, direct_isolated: set) -> set:
    """定義どおりの素朴な実装（祖先をすべて調べる）。O(V × (V + E))。"""
    return {
        v for v in G_after.nodes()
        if v not in direct_isolated
        and (anc := nx.ancestors(G_after, v))
        and anc <= direct_isolated
    }


# ---------------------------------------------------------------------------
# 強橋
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(200))
def test_strong_bridges_match_naive_on_random_graphs(seed):
    rng = random.Random(seed)
    G = random_digraph(rng.randint(2, 30), rng.choice([0.05, 0.1, 0.2, 0.4]), seed, self_loops=True)
    assert set(find_strong_bridges(G)) == set(find_strong_bridges_naive(G))


def test_strong_bridges_on_cycle_are_all_edges():
    G = nx.DiGraph([("A", "B"), ("B", "C"), ("C", "A")])
    assert set(find_strong_bridges(G)) == set(G.edges())


def test_strong_bridges_on_complete_graph_are_none():
    assert find_strong_bridges(nx.complete_graph(5, create_using=nx.DiGraph)) == []


def test_strong_bridges_do_not_modify_input():
    G = build_demo_graph(SCENARIO_NAMES[0])
    edges_before = list(G.edges(data=True))
    find_strong_bridges(G)
    find_strong_bridges_naive(G)
    assert list(G.edges(data=True)) == edges_before  # 重み属性が消えないこと


# ---------------------------------------------------------------------------
# カスケード故障
# ---------------------------------------------------------------------------
def test_cascade_failure_on_chain():
    # X → A → B → C で X が停止
    # → A は入次数0で直接孤立、C は出次数0で直接孤立、B は補給元が A だけなのでカスケード故障
    G = nx.DiGraph([("X", "A"), ("A", "B"), ("B", "C")])
    result = simulate_failure(G, failed_nodes=["X"])
    assert result.isolated_no_input == ["A"]
    assert result.isolated_no_output == ["C"]
    assert result.cascade_failures == {"B"}


@pytest.mark.parametrize("seed", range(200))
def test_cascade_failures_match_naive_on_random_graphs(seed):
    rng = random.Random(seed)
    G = random_digraph(rng.randint(2, 30), rng.choice([0.05, 0.1, 0.2]), seed, self_loops=True)
    failed = rng.sample(list(G.nodes()), k=rng.randint(0, max(1, len(G) // 4)))
    G_after = G.copy()
    G_after.remove_nodes_from(failed)
    isolated = {n for n in G_after if G_after.in_degree(n) == 0 or G_after.out_degree(n) == 0}
    assert find_cascade_failures(G_after, isolated) == cascade_failures_naive(G_after, isolated)


# ---------------------------------------------------------------------------
# デモシナリオ：説明文の主張が実際に成り立つか
# ---------------------------------------------------------------------------
def test_scenario1_strong_bridges_are_the_dead_end_routes():
    G = build_demo_graph(SCENARIO_NAMES[0])
    expected = {
        ("高崎", "長野"), ("長野", "高崎"),
        ("八王子", "甲府"), ("甲府", "八王子"),
        ("厚木", "御殿場"), ("御殿場", "厚木"),
        ("御殿場", "静岡"), ("静岡", "御殿場"),
    }
    assert set(find_strong_bridges(G)) == expected


def test_scenario2_gotemba_failure_isolates_shizuoka():
    G = build_demo_graph(SCENARIO_NAMES[1])
    result = simulate_failure(G, failed_nodes=DEMO_SCENARIOS[SCENARIO_NAMES[1]]["demo_failed_nodes"])
    assert result.isolated_complete == ["静岡"]


def test_scenario3_tokyo_yokohama_detour_costs_85km():
    name = SCENARIO_NAMES[2]
    G = build_demo_graph(name)
    failed = DEMO_SCENARIOS[name]["demo_failed_edges"]
    result = simulate_failure(G, failed_edges=failed)
    table = analyze_rerouting_cost(G, result.G_after, failed)
    assert list(table["障害前コスト"]) == ["30.0", "30.0"]
    assert list(table["障害後コスト"]) == ["85.0", "85.0"]


def test_rerouting_cost_survives_strong_bridge_analysis():
    """強橋分析のあとでも迂回コストが km 単位で計算されること（以前のバグの回帰テスト）。"""
    name = SCENARIO_NAMES[2]
    G = build_demo_graph(name)
    find_strong_bridges(G)
    failed = DEMO_SCENARIOS[name]["demo_failed_edges"]
    table = analyze_rerouting_cost(G, simulate_failure(G, failed_edges=failed).G_after, failed)
    assert list(table["障害後コスト"]) == ["85.0", "85.0"]
