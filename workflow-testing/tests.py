import pytest
from main import graph


@pytest.mark.parametrize(
    "email, expected_category, expected_score",
    [
        ("this is urgent!", "urgent", 10),
        ("i wanna talk to you!", "normal", 5),
        ("i have an offer for you!", "spam", 1),
    ],
)
def test_full_graph(email, expected_category, expected_score):
    result = graph.invoke(
        {"email": email},
        config={
            "configurable": {
                "thread_id": "1",
            },
        },
    )

    assert result["category"] == expected_category
    assert result["priority_score"] == expected_score


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
        }
    )
    assert result["priority_score"] == 1

    result = graph.nodes["draft_response"].invoke(
        {
            "category": "spam",
        }
    )
    assert "Go away!" in result["response"]


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

    assert result["priority_score"] == 1
