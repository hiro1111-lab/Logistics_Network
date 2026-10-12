"""強橋検出の実行時間を、素朴な方法と支配木を用いる方法で比較する。

実行: python -m benchmarks.benchmark_strong_bridges

2種類のネットワークで測定する。
- ランダム：ランダムな有向グラフ（＋全体を強連結にする閉路1本）
- 幹線でつながる地域網：5拠点の地域（双方向の環状道路）を、1本の幹線（双方向）で
  直列につないだもの。幹線の両側に大きな領域があるため、素朴な方法の到達判定が
  毎回グラフ全体を探索することになり、素朴な方法にとって最悪に近いケースになる
"""
import time

import networkx as nx

from algorithms import find_strong_bridges, find_strong_bridges_naive

SIZES = [1000, 2000, 4000, 8000]


def random_network(n: int, seed: int = 0) -> nx.DiGraph:
    G = nx.gnp_random_graph(n, 2.0 / n, seed=seed, directed=True)
    G.add_edges_from((i, (i + 1) % n) for i in range(n))
    return G


def chained_regions_network(n: int, region_size: int = 5) -> nx.DiGraph:
    G = nx.DiGraph()
    for r in range(n // region_size):
        nodes = [r * region_size + i for i in range(region_size)]
        for a, b in zip(nodes, nodes[1:] + nodes[:1]):  # 地域内の環状道路
            G.add_edge(a, b)
            G.add_edge(b, a)
        if r > 0:  # 1つ前の地域と幹線で結ぶ
            G.add_edge(nodes[0] - 1, nodes[0])
            G.add_edge(nodes[0], nodes[0] - 1)
    return G


def best_time(func, G, repeat: int) -> float:
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        func(G)
        best = min(best, time.perf_counter() - start)
    return best


def main() -> None:
    for label, make in [("ランダム", random_network), ("幹線でつながる地域網", chained_regions_network)]:
        print(f"\n### {label}\n")
        print("| 拠点数 V | ルート数 E | 強橋の数 | 素朴な方法 | 支配木を用いる方法 | 比 |")
        print("|---:|---:|---:|---:|---:|---:|")
        for n in SIZES:
            G = make(n)
            bridges = find_strong_bridges(G)
            assert set(bridges) == set(find_strong_bridges_naive(G))
            fast = best_time(find_strong_bridges, G, repeat=3)
            naive = best_time(find_strong_bridges_naive, G, repeat=1)
            print(f"| {n:,} | {G.number_of_edges():,} | {len(bridges):,} "
                  f"| {naive:.2f} 秒 | {fast:.2f} 秒 | {naive / fast:.1f}倍 |")


if __name__ == "__main__":
    main()
