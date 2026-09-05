from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class _RouteStats:
    count: int = 0
    errors: int = 0
    latency_ms: deque[float] = field(default_factory=lambda: deque(maxlen=1000))


@dataclass
class _ModelStats:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    cost_observations: int = 0


class TelemetryRegistry:
    """Low-cardinality, process-local operational metrics.

    It deliberately stores no raw questions, answer text, source excerpts, IP addresses or
    other user-provided content. Production deployments can export the same structured logs
    to a dedicated observability backend later.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._routes: dict[str, _RouteStats] = defaultdict(_RouteStats)
        self._cache_hits: dict[str, int] = defaultdict(int)
        self._cache_misses: dict[str, int] = defaultdict(int)
        self._rate_limited = 0
        self._models: dict[str, _ModelStats] = defaultdict(_ModelStats)

    def record_request(self, method: str, path: str, status_code: int, latency_ms: float) -> None:
        key = f"{method.upper()} {path}"
        with self._lock:
            stats = self._routes[key]
            stats.count += 1
            if status_code >= 500:
                stats.errors += 1
            stats.latency_ms.append(latency_ms)

    def record_cache(self, resource: str, *, hit: bool) -> None:
        with self._lock:
            if hit:
                self._cache_hits[resource] += 1
            else:
                self._cache_misses[resource] += 1

    def record_rate_limited(self) -> None:
        with self._lock:
            self._rate_limited += 1

    def record_model(
        self,
        *,
        provider: str,
        model: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        estimated_cost_usd: float | None,
    ) -> None:
        key = f"{provider}:{model}"
        with self._lock:
            stats = self._models[key]
            stats.calls += 1
            stats.prompt_tokens += prompt_tokens or 0
            stats.completion_tokens += completion_tokens or 0
            if estimated_cost_usd is not None:
                stats.estimated_cost_usd += estimated_cost_usd
                stats.cost_observations += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            routes = {
                key: {
                    "count": stats.count,
                    "errors_5xx": stats.errors,
                    "latency_ms": _latency_summary(list(stats.latency_ms)),
                }
                for key, stats in sorted(self._routes.items())
            }
            cache_resources = sorted(set(self._cache_hits) | set(self._cache_misses))
            cache = {
                resource: {
                    "hits": self._cache_hits[resource],
                    "misses": self._cache_misses[resource],
                    "hit_rate": _hit_rate(
                        self._cache_hits[resource], self._cache_misses[resource]
                    ),
                }
                for resource in cache_resources
            }
            models = {
                key: {
                    "calls": stats.calls,
                    "prompt_tokens": stats.prompt_tokens,
                    "completion_tokens": stats.completion_tokens,
                    "estimated_cost_usd": round(stats.estimated_cost_usd, 8),
                    "cost_observations": stats.cost_observations,
                }
                for key, stats in sorted(self._models.items())
            }
            return {
                "requests": routes,
                "cache": cache,
                "rate_limited_requests": self._rate_limited,
                "models": models,
                "privacy": {
                    "raw_queries_recorded": False,
                    "answer_text_recorded": False,
                    "client_ip_recorded": False,
                },
            }


def _latency_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"samples": 0, "p50": None, "p95": None, "p99": None, "max": None}
    ordered = sorted(values)
    return {
        "samples": len(ordered),
        "p50": round(_percentile(ordered, 0.50), 3),
        "p95": round(_percentile(ordered, 0.95), 3),
        "p99": round(_percentile(ordered, 0.99), 3),
        "max": round(ordered[-1], 3),
    }


def _percentile(ordered: list[float], fraction: float) -> float:
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def _hit_rate(hits: int, misses: int) -> float | None:
    total = hits + misses
    if total == 0:
        return None
    return round(hits / total, 6)
