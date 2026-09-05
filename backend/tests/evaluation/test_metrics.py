from app.evaluation.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank


def test_retrieval_metrics() -> None:
    retrieved = ["x", "b", "c"]
    relevant = {"b", "d"}
    assert recall_at_k(retrieved, relevant, 3) == 0.5
    assert precision_at_k(retrieved, relevant, 3) == 1 / 3
    assert reciprocal_rank(retrieved, relevant) == 0.5
    assert 0 < ndcg_at_k(retrieved, relevant, 3) < 1
