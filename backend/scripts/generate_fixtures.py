"""Script to generate all 26 IR test fixtures."""

import json
from pathlib import Path

fixtures = {
    "cover.json": {
        "schema_version": 1,
        "slide_key": "s1",
        "layout": "cover",
        "title": "Modern Cloud Architecture",
        "subtitle": "Scalable Systems and Microservices Design Patterns",
        "blocks": [],
    },
    "section.json": {
        "schema_version": 1,
        "slide_key": "s2",
        "layout": "section",
        "title": "Part 1: Foundational Infrastructure",
        "blocks": [],
    },
    "statement.json": {
        "schema_version": 1,
        "slide_key": "s3",
        "layout": "statement",
        "title": "Core Philosophy",
        "blocks": [
            {
                "type": "text",
                "style": "quote",
                "items": [
                    "Simplicity is prerequisite for reliability. Complex systems always fail in complex ways."
                ],
            }
        ],
    },
    "text.json": {
        "schema_version": 1,
        "slide_key": "s4",
        "layout": "text",
        "title": "System Design Principles",
        "blocks": [
            {
                "type": "text",
                "style": "bullets",
                "items": [
                    "Isolate stateful components from stateless web tier",
                    "Design for failure with circuit breakers and timeouts",
                    "Adopt asynchronous messaging for high decoupling",
                    "Instrument every service with end-to-end tracing",
                ],
            }
        ],
    },
    "two_column.json": {
        "schema_version": 1,
        "slide_key": "s5",
        "layout": "two_column",
        "title": "Monolith vs Microservices",
        "blocks": [
            {
                "type": "text",
                "style": "bullets",
                "heading": "Monolithic Approach",
                "items": [
                    "Single codebase and deployment unit",
                    "Simple local testing and debugging",
                    "Tight coupling impedes autonomous scaling",
                ],
            },
            {
                "type": "text",
                "style": "bullets",
                "heading": "Distributed Services",
                "items": [
                    "Independently deployable bounded contexts",
                    "Targeted autoscaling of hot services",
                    "Operational overhead requiring robust observability",
                ],
            },
        ],
    },
    "split.json": {
        "schema_version": 1,
        "slide_key": "s6",
        "layout": "split",
        "title": "Event-Driven Processing",
        "text_side": "left",
        "blocks": [
            {
                "type": "text",
                "style": "bullets",
                "heading": "Workflow Overview",
                "items": [
                    "Incoming requests produce audit events",
                    "Stream processor enriches payload",
                    "Analytics engine ingests in real-time",
                ],
            },
            {
                "type": "diagram",
                "kind": "flow",
                "direction": "LR",
                "nodes": [
                    {
                        "id": "ingress",
                        "label": "API Ingress",
                        "shape": "rounded",
                        "emphasis": "primary",
                    },
                    {"id": "bus", "label": "Event Bus", "shape": "rect", "emphasis": "accent"},
                    {
                        "id": "sink",
                        "label": "Data Sink",
                        "shape": "rounded",
                        "emphasis": "positive",
                    },
                ],
                "edges": [
                    {"source": "ingress", "target": "bus", "label": "publish"},
                    {"source": "bus", "target": "sink", "label": "consume"},
                ],
            },
        ],
    },
    "image_text.json": {
        "schema_version": 1,
        "slide_key": "s7",
        "layout": "image_text",
        "title": "User Experience Benchmark",
        "image_side": "left",
        "blocks": [
            {
                "type": "image",
                "asset_id": "asset_sample_chart_1",
                "caption": "Quarterly Latency Distribution (p99)",
            },
            {
                "type": "text",
                "style": "bullets",
                "items": [
                    "Sub-100ms response times maintained across regions",
                    "Zero dropped transactions during traffic spikes",
                    "Linear caching efficiency achieved via edge proxies",
                ],
            },
        ],
    },
    "closing.json": {
        "schema_version": 1,
        "slide_key": "s8",
        "layout": "closing",
        "title": "Thank You",
        "subtitle": "Questions & Discussion",
        "blocks": [
            {
                "type": "text",
                "style": "bullets",
                "items": [
                    "Docs: https://github.com/excali-slide",
                    "Contact: team@excalislide.dev",
                ],
            }
        ],
    },
    "diagram_flow_lr.json": {
        "schema_version": 1,
        "slide_key": "s9",
        "layout": "diagram",
        "title": "Data Ingestion Pipeline",
        "blocks": [
            {
                "type": "diagram",
                "kind": "flow",
                "direction": "LR",
                "nodes": [
                    {
                        "id": "source",
                        "label": "Raw Sources",
                        "shape": "rounded",
                        "emphasis": "normal",
                    },
                    {
                        "id": "parser",
                        "label": "Format Parser",
                        "shape": "rounded",
                        "emphasis": "primary",
                    },
                    {
                        "id": "validator",
                        "label": "Schema Gate",
                        "shape": "diamond",
                        "emphasis": "accent",
                    },
                    {"id": "db", "label": "Warehouse", "shape": "rounded", "emphasis": "positive"},
                ],
                "edges": [
                    {"source": "source", "target": "parser"},
                    {"source": "parser", "target": "validator"},
                    {"source": "validator", "target": "db", "label": "valid"},
                ],
            }
        ],
    },
    "diagram_flow_tb_groups.json": {
        "schema_version": 1,
        "slide_key": "s10",
        "layout": "diagram",
        "title": "Tiered Security Architecture",
        "blocks": [
            {
                "type": "diagram",
                "kind": "flow",
                "direction": "TB",
                "groups": [
                    {"id": "dmz", "label": "Public DMZ"},
                    {"id": "internal", "label": "Private Network"},
                ],
                "nodes": [
                    {
                        "id": "waf",
                        "label": "Cloud WAF",
                        "shape": "rounded",
                        "emphasis": "primary",
                        "group_id": "dmz",
                    },
                    {
                        "id": "gateway",
                        "label": "API Gateway",
                        "shape": "rounded",
                        "emphasis": "accent",
                        "group_id": "dmz",
                    },
                    {
                        "id": "auth",
                        "label": "OAuth Server",
                        "shape": "rounded",
                        "emphasis": "normal",
                        "group_id": "internal",
                    },
                    {
                        "id": "service",
                        "label": "Core Engine",
                        "shape": "rounded",
                        "emphasis": "positive",
                        "group_id": "internal",
                    },
                ],
                "edges": [
                    {"source": "waf", "target": "gateway"},
                    {"source": "gateway", "target": "auth"},
                    {"source": "gateway", "target": "service"},
                ],
            }
        ],
    },
    "diagram_hierarchy.json": {
        "schema_version": 1,
        "slide_key": "s11",
        "layout": "diagram",
        "title": "Organization Hierarchy",
        "blocks": [
            {
                "type": "diagram",
                "kind": "hierarchy",
                "direction": "TB",
                "nodes": [
                    {
                        "id": "ceo",
                        "label": "Chief Executive",
                        "shape": "rounded",
                        "emphasis": "primary",
                    },
                    {
                        "id": "vp_eng",
                        "label": "VP Engineering",
                        "shape": "rounded",
                        "emphasis": "accent",
                    },
                    {
                        "id": "vp_prod",
                        "label": "VP Product",
                        "shape": "rounded",
                        "emphasis": "accent",
                    },
                    {
                        "id": "lead_be",
                        "label": "Backend Team",
                        "shape": "rect",
                        "emphasis": "normal",
                    },
                    {
                        "id": "lead_fe",
                        "label": "Frontend Team",
                        "shape": "rect",
                        "emphasis": "normal",
                    },
                ],
                "edges": [
                    {"source": "ceo", "target": "vp_eng"},
                    {"source": "ceo", "target": "vp_prod"},
                    {"source": "vp_eng", "target": "lead_be"},
                    {"source": "vp_eng", "target": "lead_fe"},
                ],
            }
        ],
    },
    "diagram_layers.json": {
        "schema_version": 1,
        "slide_key": "s12",
        "layout": "diagram",
        "title": "Application Stack Layers",
        "blocks": [
            {
                "type": "diagram",
                "kind": "layers",
                "nodes": [
                    {
                        "id": "l_ui",
                        "label": "Presentation Layer",
                        "sublabel": "React + TypeScript",
                        "emphasis": "primary",
                    },
                    {
                        "id": "l_api",
                        "label": "API Gateway Tier",
                        "sublabel": "FastAPI + REST",
                        "emphasis": "accent",
                    },
                    {
                        "id": "l_domain",
                        "label": "Business Logic Tier",
                        "sublabel": "Pure Domain Models",
                        "emphasis": "normal",
                    },
                    {
                        "id": "l_persist",
                        "label": "Persistence Tier",
                        "sublabel": "PostgreSQL + S3",
                        "emphasis": "positive",
                    },
                ],
                "edges": [],
            }
        ],
    },
    "diagram_cycle.json": {
        "schema_version": 1,
        "slide_key": "s13",
        "layout": "diagram",
        "title": "Continuous Delivery Lifecycle",
        "blocks": [
            {
                "type": "diagram",
                "kind": "cycle",
                "caption": "DevOps Loop",
                "nodes": [
                    {"id": "plan", "label": "Plan", "shape": "rounded", "emphasis": "primary"},
                    {"id": "code", "label": "Code", "shape": "rounded", "emphasis": "normal"},
                    {"id": "build", "label": "Build", "shape": "rounded", "emphasis": "accent"},
                    {"id": "test", "label": "Test", "shape": "rounded", "emphasis": "positive"},
                    {"id": "deploy", "label": "Deploy", "shape": "rounded", "emphasis": "negative"},
                ],
                "edges": [],
            }
        ],
    },
    "diagram_timeline.json": {
        "schema_version": 1,
        "slide_key": "s14",
        "layout": "diagram",
        "title": "Engineering Roadmap 2026",
        "blocks": [
            {
                "type": "diagram",
                "kind": "timeline",
                "nodes": [
                    {
                        "id": "q1",
                        "label": "Q1 Launch",
                        "sublabel": "Beta rollout",
                        "emphasis": "primary",
                    },
                    {
                        "id": "q2",
                        "label": "Q2 Scale",
                        "sublabel": "Multi-region setup",
                        "emphasis": "accent",
                    },
                    {
                        "id": "q3",
                        "label": "Q3 Enterprise",
                        "sublabel": "SSO & RBAC",
                        "emphasis": "positive",
                    },
                    {
                        "id": "q4",
                        "label": "Q4 Automation",
                        "sublabel": "Self-healing jobs",
                        "emphasis": "normal",
                    },
                ],
                "edges": [],
            }
        ],
    },
    "diagram_comparison.json": {
        "schema_version": 1,
        "slide_key": "s15",
        "layout": "diagram",
        "title": "Deployment Strategy Comparison",
        "blocks": [
            {
                "type": "diagram",
                "kind": "comparison",
                "groups": [
                    {"id": "canary", "label": "Canary Release"},
                    {"id": "bluegreen", "label": "Blue-Green"},
                    {"id": "rolling", "label": "Rolling Update"},
                ],
                "nodes": [
                    {
                        "id": "c1",
                        "label": "Low Risk Exposure",
                        "group_id": "canary",
                        "emphasis": "positive",
                    },
                    {
                        "id": "c2",
                        "label": "Requires Traffic Splitter",
                        "group_id": "canary",
                        "emphasis": "muted",
                    },
                    {
                        "id": "bg1",
                        "label": "Instant Rollback",
                        "group_id": "bluegreen",
                        "emphasis": "positive",
                    },
                    {
                        "id": "bg2",
                        "label": "2x Infrastructure Cost",
                        "group_id": "bluegreen",
                        "emphasis": "negative",
                    },
                    {
                        "id": "r1",
                        "label": "Minimal Overhead",
                        "group_id": "rolling",
                        "emphasis": "normal",
                    },
                    {
                        "id": "r2",
                        "label": "Mixed Version Window",
                        "group_id": "rolling",
                        "emphasis": "accent",
                    },
                ],
                "edges": [],
            }
        ],
    },
    "diagram_mindmap.json": {
        "schema_version": 1,
        "slide_key": "s16",
        "layout": "diagram",
        "title": "Software Quality Attributes",
        "blocks": [
            {
                "type": "diagram",
                "kind": "mindmap",
                "nodes": [
                    {
                        "id": "root",
                        "label": "System Quality",
                        "shape": "ellipse",
                        "emphasis": "primary",
                    },
                    {"id": "rel", "label": "Reliability", "shape": "rounded", "emphasis": "accent"},
                    {"id": "sec", "label": "Security", "shape": "rounded", "emphasis": "positive"},
                    {
                        "id": "perf",
                        "label": "Performance",
                        "shape": "rounded",
                        "emphasis": "normal",
                    },
                    {
                        "id": "rel_ha",
                        "label": "High Availability",
                        "shape": "rect",
                        "emphasis": "muted",
                    },
                    {"id": "sec_auth", "label": "Zero Trust", "shape": "rect", "emphasis": "muted"},
                    {
                        "id": "perf_lat",
                        "label": "Low Latency",
                        "shape": "rect",
                        "emphasis": "muted",
                    },
                ],
                "edges": [
                    {"source": "root", "target": "rel"},
                    {"source": "root", "target": "sec"},
                    {"source": "root", "target": "perf"},
                    {"source": "rel", "target": "rel_ha"},
                    {"source": "sec", "target": "sec_auth"},
                    {"source": "perf", "target": "perf_lat"},
                ],
            }
        ],
    },
    "single_node_flow.json": {
        "schema_version": 1,
        "slide_key": "s17",
        "layout": "diagram",
        "title": "Single Service Node",
        "blocks": [
            {
                "type": "diagram",
                "kind": "flow",
                "direction": "LR",
                "nodes": [
                    {
                        "id": "solo",
                        "label": "Autonomous Agent",
                        "shape": "rounded",
                        "emphasis": "primary",
                    }
                ],
                "edges": [],
            }
        ],
    },
    "disconnected_flow.json": {
        "schema_version": 1,
        "slide_key": "s18",
        "layout": "diagram",
        "title": "Disconnected Components",
        "blocks": [
            {
                "type": "diagram",
                "kind": "flow",
                "direction": "LR",
                "nodes": [
                    {"id": "a", "label": "Cluster A", "shape": "rounded", "emphasis": "primary"},
                    {"id": "b", "label": "Cluster B", "shape": "rounded", "emphasis": "accent"},
                    {"id": "c", "label": "Isolated Node", "shape": "rounded", "emphasis": "muted"},
                ],
                "edges": [{"source": "a", "target": "b"}],
            }
        ],
    },
    "cycle_flow.json": {
        "schema_version": 1,
        "slide_key": "s19",
        "layout": "diagram",
        "title": "Bidirectional Feedback Flow",
        "blocks": [
            {
                "type": "diagram",
                "kind": "flow",
                "direction": "LR",
                "nodes": [
                    {
                        "id": "ctrl",
                        "label": "Controller",
                        "shape": "rounded",
                        "emphasis": "primary",
                    },
                    {"id": "act", "label": "Actuator", "shape": "rounded", "emphasis": "accent"},
                ],
                "edges": [
                    {"source": "ctrl", "target": "act", "label": "command"},
                    {"source": "act", "target": "ctrl", "label": "telemetry"},
                ],
            }
        ],
    },
    "hard_cap_flow_16.json": {
        "schema_version": 1,
        "slide_key": "s20",
        "layout": "diagram",
        "title": "16-Node Maximum Capacity Flow",
        "blocks": [
            {
                "type": "diagram",
                "kind": "flow",
                "direction": "LR",
                "nodes": [
                    {"id": f"n{i}", "label": f"Node {i}", "shape": "rounded", "emphasis": "normal"}
                    for i in range(16)
                ],
                "edges": [{"source": f"n{i}", "target": f"n{i + 1}"} for i in range(15)],
            }
        ],
    },
    "long_labels.json": {
        "schema_version": 1,
        "slide_key": "s21",
        "layout": "diagram",
        "title": "Comprehensive Workflow Specification",
        "blocks": [
            {
                "type": "diagram",
                "kind": "flow",
                "direction": "LR",
                "nodes": [
                    {
                        "id": "step1",
                        "label": "Initialize Secure Storage Cluster",
                        "sublabel": "Zero-knowledge encryption keys",
                        "shape": "rounded",
                        "emphasis": "primary",
                    },
                    {
                        "id": "step2",
                        "label": "Propagate Distributed Replicas",
                        "sublabel": "Multi-region sync consensus",
                        "shape": "rounded",
                        "emphasis": "accent",
                    },
                ],
                "edges": [{"source": "step1", "target": "step2", "label": "replicate"}],
            }
        ],
    },
    "long_title.json": {
        "schema_version": 1,
        "slide_key": "s22",
        "layout": "text",
        "title": "A Very Detailed Investigation Into Enterprise Cloud Resilience Standards",
        "blocks": [
            {
                "type": "text",
                "style": "bullets",
                "items": [
                    "Guaranteed recovery point objectives under 30 seconds",
                    "Redundant geo-distributed data plane routing",
                ],
            }
        ],
    },
    "max_bullets_6.json": {
        "schema_version": 1,
        "slide_key": "s23",
        "layout": "text",
        "title": "Key Deployment Milestones",
        "blocks": [
            {
                "type": "text",
                "style": "numbered",
                "items": [
                    "Provision virtual private cloud and subnets with strict route tables",
                    "Configure security groups and ingress access control policies",
                    "Deploy database clusters with multi-AZ failover replication",
                    "Initialize Redis caching layer with automated sharding support",
                    "Bootstrap backend microservices and verify health endpoints",
                    "Switch DNS traffic via global latency-based routing policies",
                ],
            }
        ],
    },
    "image_text_tall.json": {
        "schema_version": 1,
        "slide_key": "s24",
        "layout": "image_text",
        "title": "Mobile App Prototype",
        "image_side": "left",
        "blocks": [
            {
                "type": "image",
                "asset_id": "tall_mockup_asset",
                "caption": "iOS Portrait Viewport",
            },
            {
                "type": "text",
                "style": "bullets",
                "items": [
                    "Native gesture support with haptic feedback",
                    "Offline-first sync via SQLite local cache",
                    "Seamless dark mode and dynamic typography",
                ],
            },
        ],
    },
    "image_text_wide.json": {
        "schema_version": 1,
        "slide_key": "s25",
        "layout": "image_text",
        "title": "Panoramic Telemetry Dashboard",
        "image_side": "right",
        "blocks": [
            {
                "type": "image",
                "asset_id": "wide_dashboard_asset",
                "caption": "Realtime Global Operations",
            },
            {
                "type": "text",
                "style": "bullets",
                "items": [
                    "Live traffic visualization across 24 edge nodes",
                    "Automated anomaly alerts integrated with PagerDuty",
                ],
            },
        ],
    },
    "split_text_right.json": {
        "schema_version": 1,
        "slide_key": "s26",
        "layout": "split",
        "title": "Query Execution Plan",
        "text_side": "right",
        "blocks": [
            {
                "type": "text",
                "style": "bullets",
                "heading": "Optimization Steps",
                "items": [
                    "Cost-based index selection",
                    "Hash join over nested loops",
                    "Streaming partial aggregations",
                ],
            },
            {
                "type": "diagram",
                "kind": "flow",
                "direction": "TB",
                "nodes": [
                    {"id": "scan", "label": "Index Scan", "shape": "rect", "emphasis": "normal"},
                    {"id": "join", "label": "Hash Join", "shape": "rounded", "emphasis": "primary"},
                    {"id": "out", "label": "Output", "shape": "rounded", "emphasis": "positive"},
                ],
                "edges": [
                    {"source": "scan", "target": "join"},
                    {"source": "join", "target": "out"},
                ],
            },
        ],
    },
}

out_dir = Path("tests/fixtures/ir")
out_dir.mkdir(parents=True, exist_ok=True)
for filename, content in fixtures.items():
    (out_dir / filename).write_text(json.dumps(content, indent=2), encoding="utf-8")
print(f"Generated {len(fixtures)} fixtures in {out_dir}")
