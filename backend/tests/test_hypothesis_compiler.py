"""Property-based fuzzing tests for compiler robustness using Hypothesis."""

from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from app.compiler import compile
from app.ir.schemas import DiagramBlock, Edge, Node, SlideIR

node_id_strategy = st.from_regex(re.compile(r"^[a-z][a-z0-9_]{0,10}$"), fullmatch=True)
label_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
    min_size=1,
    max_size=30,
).map(lambda s: s.strip() or "Node")


@settings(max_examples=25, deadline=None)
@given(
    num_nodes=st.integers(min_value=1, max_value=12),
    labels=st.lists(label_strategy, min_size=12, max_size=12),
)
def test_hypothesis_random_flow_compile(num_nodes: int, labels: list[str]):
    """Compile random flow graphs and verify it either cleanly succeeds or fails with diagram_too_dense."""
    nodes = [
        Node(
            id=f"n{i}",
            label=labels[i][:25],
            shape="rounded",
            emphasis="normal",
        )
        for i in range(num_nodes)
    ]

    edges = []
    for i in range(num_nodes - 1):
        edges.append(Edge(source=f"n{i}", target=f"n{i + 1}"))

    ir = SlideIR(
        schema_version=1,
        slide_key="hypo_slide",
        layout="diagram",
        title="Hypothesis Test",
        blocks=[
            DiagramBlock(
                type="diagram",
                kind="flow",
                direction="LR",
                nodes=nodes,
                edges=edges,
            )
        ],
    )

    result = compile(ir)

    if result.errors:
        assert any(
            "diagram_too_dense" in err or "cannot fit" in err or "overflow" in err
            for err in result.errors
        ), f"Unexpected compilation errors: {result.errors}"
    else:
        assert result.skeleton is not None
        elements = result.skeleton["elements"]
        frame = elements[0]
        assert frame["type"] == "frame"

        # Content elements inside frame
        for el in elements[1:]:
            if el["type"] not in ("arrow", "line"):
                assert el["x"] >= 0
                assert el["y"] >= 0
                assert el["x"] + el["width"] <= 1920
                assert el["y"] + el["height"] <= 1080
