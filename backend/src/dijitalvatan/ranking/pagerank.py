"""PageRank exactly as in the course notebook: no redistribution of rank from pages without outlinks."""

Graph = dict[str, list[str]]


def compute_ranks(graph: Graph, damping: float, iterations: int) -> dict[str, float]:
    urls = list(graph)
    if not urls:
        return {}
    incoming: dict[str, list[str]] = {url: [] for url in urls}
    for source in urls:
        for target in dict.fromkeys(graph[source]):
            if target in incoming:
                incoming[target].append(source)
    ranks = {url: 1 / len(urls) for url in urls}
    for _ in range(iterations):
        ranks = {
            url: (1 - damping) / len(urls) + sum(damping * ranks[source] / len(graph[source]) for source in incoming[url])
            for url in urls
        }
    return ranks
