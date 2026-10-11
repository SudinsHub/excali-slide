"""Comprehensive unit tests for SlideIR cross-field validators."""

from __future__ import annotations

from app.ir import (
    Budgets,
    DiagramBlock,
    Edge,
    Group,
    Node,
    SlideIR,
    TextBlock,
    validate_ir,
)


def test_missing_title_and_subtitle_cover():
    ir = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="cover",
        title=None,
        subtitle=None,
    )
    issues = validate_ir(ir)
    codes = {i.code for i in issues}
    assert "missing_title" in codes
    assert "missing_subtitle" in codes
    assert any(i.message == "cover layout requires a non-empty title" for i in issues)
    assert any(i.message == "cover layout requires a non-empty subtitle" for i in issues)


def test_title_too_long():
    ir = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="text",
        title="A" * 71,
        blocks=[TextBlock(type="text", style="bullets", items=["Item"])],
    )
    issues = validate_ir(ir)
    assert any(i.code == "title_too_long" for i in issues)
    assert any("title exceeds maximum 70 characters (got 71)" in i.message for i in issues)


def test_cover_with_blocks_rejected():
    ir = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="cover",
        title="Title",
        subtitle="Subtitle",
        blocks=[TextBlock(type="text", style="bullets", items=["Item"])],
    )
    issues = validate_ir(ir)
    assert any(i.code == "invalid_blocks" and "cover layout must not contain blocks, got 1" in i.message for i in issues)


def test_closing_bullet_cap():
    ir = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="closing",
        title="Title",
        subtitle="Subtitle",
        blocks=[TextBlock(type="text", style="bullets", items=["1", "2", "3", "4"])],
    )
    issues = validate_ir(ir)
    assert any(i.code == "too_many_bullets" and "closing layout allows at most 3 bullets, got 4" in i.message for i in issues)


def test_statement_rules():
    ir_bad = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="statement",
        blocks=[TextBlock(type="text", style="bullets", items=["Item 1", "Item 2"])],
    )
    issues = validate_ir(ir_bad)
    assert any(i.code == "invalid_text_style" for i in issues)
    assert any(i.code == "statement_item_count" for i in issues)


def test_two_column_headings_required():
    ir = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="two_column",
        title="Title",
        blocks=[
            TextBlock(type="text", style="bullets", heading="Heading 1", items=["Item 1"]),
            TextBlock(type="text", style="bullets", heading=None, items=["Item 2"]),
        ],
    )
    issues = validate_ir(ir)
    assert any(i.code == "missing_column_heading" for i in issues)


def test_cycle_node_count_constraint():
    ir_too_few = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="diagram",
        title="Cycle",
        blocks=[
            DiagramBlock(
                type="diagram",
                kind="cycle",
                nodes=[
                    Node(id="n1", label="Node 1"),
                    Node(id="n2", label="Node 2"),
                ],
            )
        ],
    )
    issues = validate_ir(ir_too_few)
    assert any(i.code == "invalid_node_count_cycle" for i in issues)
    assert any("cycle diagrams need 3-8 nodes, got 2" in i.message for i in issues)


def test_timeline_node_count_constraint():
    nodes = [Node(id=f"n{i}", label=f"M{i}") for i in range(8)]
    ir = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="diagram",
        title="Timeline",
        blocks=[DiagramBlock(type="diagram", kind="timeline", nodes=nodes)],
    )
    issues = validate_ir(ir)
    assert any(i.code == "invalid_node_count_timeline" and "timeline diagrams need 3-7 nodes, got 8" in i.message for i in issues)


def test_comparison_group_and_node_rules():
    ir = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="diagram",
        title="Comparison",
        blocks=[
            DiagramBlock(
                type="diagram",
                kind="comparison",
                groups=[Group(id="g1", label="Group 1")],
                nodes=[Node(id="n1", label="Node 1")],
            )
        ],
    )
    issues = validate_ir(ir)
    assert any(i.code == "invalid_group_count_comparison" and "comparison diagrams need 2-3 groups, got 1" in i.message for i in issues)


def test_edge_references_and_no_self_loops():
    ir = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="diagram",
        title="Flow",
        blocks=[
            DiagramBlock(
                type="diagram",
                kind="flow",
                nodes=[Node(id="a", label="A"), Node(id="b", label="B")],
                edges=[
                    Edge(source="a", target="ghost"),
                    Edge(source="a", target="a"),
                ],
            )
        ],
    )
    issues = validate_ir(ir)
    assert any(i.code == "edge_invalid_target" and "edge target 'ghost' does not exist in nodes" in i.message for i in issues)
    assert any(i.code == "self_loop_forbidden" and "self-loop on node 'a' is forbidden" in i.message for i in issues)


def test_tree_rules_hierarchy_and_mindmap():
    # Disconnected hierarchy
    ir_disc = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="diagram",
        title="Hierarchy",
        blocks=[
            DiagramBlock(
                type="diagram",
                kind="hierarchy",
                nodes=[Node(id="r1", label="R1"), Node(id="r2", label="R2"), Node(id="c1", label="C1")],
                edges=[Edge(source="r1", target="c1")],
            )
        ],
    )
    issues = validate_ir(ir_disc)
    assert any(i.code == "tree_single_root_violation" for i in issues)

    # Mindmap depth > 2
    ir_deep_mindmap = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="diagram",
        title="Mindmap",
        blocks=[
            DiagramBlock(
                type="diagram",
                kind="mindmap",
                nodes=[
                    Node(id="root", label="Root"),
                    Node(id="l1", label="Level 1"),
                    Node(id="l2", label="Level 2"),
                    Node(id="l3", label="Level 3"),
                ],
                edges=[
                    Edge(source="root", target="l1"),
                    Edge(source="l1", target="l2"),
                    Edge(source="l2", target="l3"),
                ],
            )
        ],
    )
    issues_mm = validate_ir(ir_deep_mindmap)
    assert any(i.code == "mindmap_depth_exceeded" and "mindmap diagrams cap depth at 2" in i.message for i in issues_mm)


def test_budget_warnings_vs_hard_caps():
    budgets = Budgets(max_nodes=4, bullets=2, words_per_bullet=3, diagram_share=0.5)

    # Text exceeding budget bullets and words
    ir = SlideIR(
        schema_version=1,
        slide_key="s1",
        layout="text",
        title="Text",
        blocks=[
            TextBlock(
                type="text",
                style="bullets",
                items=[
                    "This is a long sentence exceeding three words",
                    "Second bullet",
                    "Third bullet exceeding budget",
                ],
            )
        ],
    )
    issues = validate_ir(ir, budgets=budgets)
    warnings = [i for i in issues if i.severity == "warning"]
    assert any(w.code == "budget_bullets_exceeded" for w in warnings)
    assert any(w.code == "budget_words_exceeded" for w in warnings)
