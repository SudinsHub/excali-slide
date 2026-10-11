export const FIXTURES: Record<string, any> = {
  'cover.json': {
    schema_version: 1,
    slide_key: 's1',
    layout: 'cover',
    title: 'Modern Cloud Architecture',
    subtitle: 'Scalable Systems and Microservices Design Patterns',
    blocks: [],
  },
  'section.json': {
    schema_version: 1,
    slide_key: 's2',
    layout: 'section',
    title: 'Part 1: Foundational Infrastructure',
    blocks: [],
  },
  'statement.json': {
    schema_version: 1,
    slide_key: 's3',
    layout: 'statement',
    title: 'Core Philosophy',
    blocks: [
      {
        type: 'text',
        style: 'quote',
        items: [
          'Simplicity is prerequisite for reliability. Complex systems always fail in complex ways.',
        ],
      },
    ],
  },
  'text.json': {
    schema_version: 1,
    slide_key: 's4',
    layout: 'text',
    title: 'System Design Principles',
    blocks: [
      {
        type: 'text',
        style: 'bullets',
        items: [
          'Isolate stateful components from stateless web tier',
          'Design for failure with circuit breakers and timeouts',
          'Adopt asynchronous messaging for high decoupling',
          'Instrument every service with end-to-end tracing',
        ],
      },
    ],
  },
  'two_column.json': {
    schema_version: 1,
    slide_key: 's5',
    layout: 'two_column',
    title: 'Monolith vs Microservices',
    blocks: [
      {
        type: 'text',
        style: 'bullets',
        heading: 'Monolithic Approach',
        items: [
          'Single codebase and deployment unit',
          'Simple local testing and debugging',
          'Tight coupling impedes autonomous scaling',
        ],
      },
      {
        type: 'text',
        style: 'bullets',
        heading: 'Distributed Services',
        items: [
          'Independently deployable bounded contexts',
          'Targeted autoscaling of hot services',
          'Operational overhead requiring robust observability',
        ],
      },
    ],
  },
  'split.json': {
    schema_version: 1,
    slide_key: 's6',
    layout: 'split',
    title: 'Event-Driven Processing',
    text_side: 'left',
    blocks: [
      {
        type: 'text',
        style: 'bullets',
        heading: 'Workflow Overview',
        items: [
          'Incoming requests produce audit events',
          'Stream processor enriches payload',
          'Analytics engine ingests in real-time',
        ],
      },
      {
        type: 'diagram',
        kind: 'flow',
        direction: 'LR',
        nodes: [
          { id: 'ingress', label: 'API Ingress', shape: 'rounded', emphasis: 'primary' },
          { id: 'bus', label: 'Event Bus', shape: 'rect', emphasis: 'accent' },
          { id: 'sink', label: 'Data Sink', shape: 'rounded', emphasis: 'positive' },
        ],
        edges: [
          { source: 'ingress', target: 'bus', label: 'publish' },
          { source: 'bus', target: 'sink', label: 'consume' },
        ],
      },
    ],
  },
  'image_text.json': {
    schema_version: 1,
    slide_key: 's7',
    layout: 'image_text',
    title: 'User Experience Benchmark',
    image_side: 'left',
    blocks: [
      {
        type: 'image',
        asset_id: 'asset_sample_chart_1',
        caption: 'Quarterly Latency Distribution (p99)',
      },
      {
        type: 'text',
        style: 'bullets',
        items: [
          'Sub-100ms response times maintained across regions',
          'Zero dropped transactions during traffic spikes',
          'Linear caching efficiency achieved via edge proxies',
        ],
      },
    ],
  },
  'closing.json': {
    schema_version: 1,
    slide_key: 's8',
    layout: 'closing',
    title: 'Thank You',
    subtitle: 'Questions & Discussion',
    blocks: [
      {
        type: 'text',
        style: 'bullets',
        items: [
          'Docs: https://github.com/excali-slide',
          'Contact: team@excalislide.dev',
        ],
      },
    ],
  },
  'diagram_flow_lr.json': {
    schema_version: 1,
    slide_key: 's9',
    layout: 'diagram',
    title: 'Data Ingestion Pipeline',
    blocks: [
      {
        type: 'diagram',
        kind: 'flow',
        direction: 'LR',
        nodes: [
          { id: 'source', label: 'Raw Sources', shape: 'rounded', emphasis: 'normal' },
          { id: 'parser', label: 'Format Parser', shape: 'rounded', emphasis: 'primary' },
          { id: 'validator', label: 'Schema Gate', shape: 'diamond', emphasis: 'accent' },
          { id: 'db', label: 'Warehouse', shape: 'rounded', emphasis: 'positive' },
        ],
        edges: [
          { source: 'source', target: 'parser' },
          { source: 'parser', target: 'validator' },
          { source: 'validator', target: 'db', label: 'valid' },
        ],
      },
    ],
  },
  'diagram_flow_tb_groups.json': {
    schema_version: 1,
    slide_key: 's10',
    layout: 'diagram',
    title: 'Tiered Security Architecture',
    blocks: [
      {
        type: 'diagram',
        kind: 'flow',
        direction: 'TB',
        groups: [
          { id: 'dmz', label: 'Public DMZ' },
          { id: 'internal', label: 'Private Network' },
        ],
        nodes: [
          { id: 'waf', label: 'Cloud WAF', shape: 'rounded', emphasis: 'primary', group_id: 'dmz' },
          { id: 'gateway', label: 'API Gateway', shape: 'rounded', emphasis: 'accent', group_id: 'dmz' },
          { id: 'auth', label: 'OAuth Server', shape: 'rounded', emphasis: 'normal', group_id: 'internal' },
          { id: 'service', label: 'Core Engine', shape: 'rounded', emphasis: 'positive', group_id: 'internal' },
        ],
        edges: [
          { source: 'waf', target: 'gateway' },
          { source: 'gateway', target: 'auth' },
          { source: 'gateway', target: 'service' },
        ],
      },
    ],
  },
  'diagram_hierarchy.json': {
    schema_version: 1,
    slide_key: 's11',
    layout: 'diagram',
    title: 'Organization Hierarchy',
    blocks: [
      {
        type: 'diagram',
        kind: 'hierarchy',
        direction: 'TB',
        nodes: [
          { id: 'ceo', label: 'Chief Executive', shape: 'rounded', emphasis: 'primary' },
          { id: 'vp_eng', label: 'VP Engineering', shape: 'rounded', emphasis: 'accent' },
          { id: 'vp_prod', label: 'VP Product', shape: 'rounded', emphasis: 'accent' },
          { id: 'lead_be', label: 'Backend Team', shape: 'rect', emphasis: 'normal' },
          { id: 'lead_fe', label: 'Frontend Team', shape: 'rect', emphasis: 'normal' },
        ],
        edges: [
          { source: 'ceo', target: 'vp_eng' },
          { source: 'ceo', target: 'vp_prod' },
          { source: 'vp_eng', target: 'lead_be' },
          { source: 'vp_eng', target: 'lead_fe' },
        ],
      },
    ],
  },
  'diagram_layers.json': {
    schema_version: 1,
    slide_key: 's12',
    layout: 'diagram',
    title: 'Application Stack Layers',
    blocks: [
      {
        type: 'diagram',
        kind: 'layers',
        nodes: [
          { id: 'l_ui', label: 'Presentation Layer', sublabel: 'React + TypeScript', emphasis: 'primary' },
          { id: 'l_api', label: 'API Gateway Tier', sublabel: 'FastAPI + REST', emphasis: 'accent' },
          { id: 'l_domain', label: 'Business Logic Tier', sublabel: 'Pure Domain Models', emphasis: 'normal' },
          { id: 'l_persist', label: 'Persistence Tier', sublabel: 'PostgreSQL + S3', emphasis: 'positive' },
        ],
        edges: [],
      },
    ],
  },
  'diagram_cycle.json': {
    schema_version: 1,
    slide_key: 's13',
    layout: 'diagram',
    title: 'Continuous Delivery Lifecycle',
    blocks: [
      {
        type: 'diagram',
        kind: 'cycle',
        caption: 'DevOps Loop',
        nodes: [
          { id: 'plan', label: 'Plan', shape: 'rounded', emphasis: 'primary' },
          { id: 'code', label: 'Code', shape: 'rounded', emphasis: 'normal' },
          { id: 'build', label: 'Build', shape: 'rounded', emphasis: 'accent' },
          { id: 'test', label: 'Test', shape: 'rounded', emphasis: 'positive' },
          { id: 'deploy', label: 'Deploy', shape: 'rounded', emphasis: 'negative' },
        ],
        edges: [],
      },
    ],
  },
  'diagram_timeline.json': {
    schema_version: 1,
    slide_key: 's14',
    layout: 'diagram',
    title: 'Engineering Roadmap 2026',
    blocks: [
      {
        type: 'diagram',
        kind: 'timeline',
        nodes: [
          { id: 'q1', label: 'Q1 Launch', sublabel: 'Beta rollout', emphasis: 'primary' },
          { id: 'q2', label: 'Q2 Scale', sublabel: 'Multi-region setup', emphasis: 'accent' },
          { id: 'q3', label: 'Q3 Enterprise', sublabel: 'SSO & RBAC', emphasis: 'positive' },
          { id: 'q4', label: 'Q4 Automation', sublabel: 'Self-healing jobs', emphasis: 'normal' },
        ],
        edges: [],
      },
    ],
  },
  'diagram_comparison.json': {
    schema_version: 1,
    slide_key: 's15',
    layout: 'diagram',
    title: 'Deployment Strategy Comparison',
    blocks: [
      {
        type: 'diagram',
        kind: 'comparison',
        groups: [
          { id: 'canary', label: 'Canary Release' },
          { id: 'bluegreen', label: 'Blue-Green' },
          { id: 'rolling', label: 'Rolling Update' },
        ],
        nodes: [
          { id: 'c1', label: 'Low Risk Exposure', group_id: 'canary', emphasis: 'positive' },
          { id: 'c2', label: 'Requires Traffic Splitter', group_id: 'canary', emphasis: 'muted' },
          { id: 'bg1', label: 'Instant Rollback', group_id: 'bluegreen', emphasis: 'positive' },
          { id: 'bg2', label: '2x Infrastructure Cost', group_id: 'bluegreen', emphasis: 'negative' },
          { id: 'r1', label: 'Minimal Overhead', group_id: 'rolling', emphasis: 'normal' },
          { id: 'r2', label: 'Mixed Version Window', group_id: 'rolling', emphasis: 'accent' },
        ],
        edges: [],
      },
    ],
  },
  'diagram_mindmap.json': {
    schema_version: 1,
    slide_key: 's16',
    layout: 'diagram',
    title: 'Software Quality Attributes',
    blocks: [
      {
        type: 'diagram',
        kind: 'mindmap',
        nodes: [
          { id: 'root', label: 'System Quality', shape: 'ellipse', emphasis: 'primary' },
          { id: 'rel', label: 'Reliability', shape: 'rounded', emphasis: 'accent' },
          { id: 'sec', label: 'Security', shape: 'rounded', emphasis: 'positive' },
          { id: 'perf', label: 'Performance', shape: 'rounded', emphasis: 'normal' },
          { id: 'rel_ha', label: 'High Availability', shape: 'rect', emphasis: 'muted' },
          { id: 'sec_auth', label: 'Zero Trust', shape: 'rect', emphasis: 'muted' },
          { id: 'perf_lat', label: 'Low Latency', shape: 'rect', emphasis: 'muted' },
        ],
        edges: [
          { source: 'root', target: 'rel' },
          { source: 'root', target: 'sec' },
          { source: 'root', target: 'perf' },
          { source: 'rel', target: 'rel_ha' },
          { source: 'sec', target: 'sec_auth' },
          { source: 'perf', target: 'perf_lat' },
        ],
      },
    ],
  },
};
