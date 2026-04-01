import pytest
from main import graph


@pytest.mark.parametrize(
    "email, expected_category, min_score, max_score",
    [
        ("this is urgent!", "urgent", 8, 10),
        ("i wanna talk to you!", "normal", 4, 7),
        ("i have an offer for you!", "spam", 1, 3),
    ],
)
def test_full_graph(email, expected_category, min_score, max_score):
    result = graph.invoke(
        {"email": email},
        config={
            "configurable": {
                "thread_id": "1",
            },
        },
    )

    assert result["category"] == expected_category
    assert min_score <= result["priority_score"] <= max_score


def test_individual_nodes():
    result = graph.nodes["categorize_email"].invoke(
        {
            "email": "i have an offer for you!",
        }
    )
    assert result["category"] == "spam"

    result = graph.nodes["assign_priority"].invoke(
        {
            "category": "spam",
            "email": "Buy this spot",
        }
    )
    assert 1 <= result["priority_score"] <= 3


def test_partial_execution():
    graph.update_state(
        # IF categorize_email node is running
        config={
            "configurable": {
                "thread_id": "1",
            },
        },
        values={
            "email": "please check out this offer",
            "category": "spam",
        },
        as_node="categorize_email",  # categorize_email 노드인것처럼 보이고 싶음.
    )

    result = graph.invoke(
        None,
        config={
            "configurable": {
                "thread_id": "1",
            },
        },
        interrupt_after="draft_response",  # Node 다음에 중단(interrupt)
    )

    assert 1 <= result["priority_score"] <= 3
