export interface DeckSettings {
  slide_count?: number | null;
  tone: 'professional' | 'casual' | 'playful' | 'technical' | 'persuasive';
  diagram_intensity: 'low' | 'medium' | 'high';
  density: 'light' | 'standard' | 'dense';
  audience: string;
  language: string;
  extra_instructions?: string;
}

export interface Deck {
  id: string;
  title: string;
  status: string;
  settings: DeckSettings;
  current_plan_id: string | null;
  slide_count: number;
  created_at: string;
  updated_at: string;
}

export interface SlideLight {
  id: string;
  position: number;
  status: string;
  title: string | null;
  current_version_id: string | null;
  draft_rev: number;
  is_dirty: boolean;
}

export interface SlideVersion {
  id: string;
  slide_id: string;
  seq: number;
  parent_version_id: string | null;
  origin: string;
  prompt: string | null;
  summary: string | null;
  ir: Record<string, any> | null;
  skeleton: Skeleton | null;
  scene: ExcalidrawScene | null;
  scene_hash: string | null;
  warnings: any[];
  created_at: string;
}

export interface VersionLight {
  id: string;
  seq: number;
  origin: string;
  summary: string | null;
  created_at: string;
  has_ir: boolean;
}

export interface SlideDraft {
  scene: ExcalidrawScene | null;
  rev: number;
  hash: string | null;
  updated_at: string | null;
}

export interface SlideDetail {
  id: string;
  deck_id: string;
  position: number;
  plan_key: string | null;
  status: string;
  error: string | null;
  current_version: SlideVersion | null;
  draft: SlideDraft | null;
  is_dirty: boolean;
}

export interface SkeletonElement {
  id: string;
  type: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
  name?: string;
  children?: string[];
  fileId?: string;
  text?: string;
  label?: {
    text: string;
    fontSize?: number;
    strokeColor?: string;
  };
  start?: { id: string };
  end?: { id: string };
  [key: string]: any;
}

export interface Skeleton {
  version: number;
  frame: { width: number; height: number };
  elements: SkeletonElement[];
  asset_ids: string[];
}

export interface ExcalidrawScene {
  elements: any[];
  appState?: Record<string, any>;
  files?: Record<string, any>;
}

export type SaveStatus = 'saved' | 'saving' | 'conflict' | 'error';

// --- Pass 3 Pipeline Interfaces ---

export interface ResourceImage {
  id: string;
  asset_id: string;
  caption: string | null;
  locator: string | null;
}

export interface Resource {
  id: string;
  deck_id: string;
  kind: string;
  filename: string;
  mime: string;
  size: number;
  status: 'uploaded' | 'parsing' | 'parsed' | 'failed';
  text: string | null;
  meta: Record<string, any> | null;
  error: string | null;
  images: ResourceImage[];
  created_at: string;
  updated_at: string;
}

export interface DiagramHint {
  kind: 'flow' | 'hierarchy' | 'layers' | 'cycle' | 'timeline' | 'comparison' | 'mindmap';
  description: string;
}

export interface PlanSlide {
  key: string;
  role: 'cover' | 'agenda' | 'section' | 'content' | 'process' | 'comparison' | 'data' | 'summary' | 'closing';
  title: string;
  kind: 'text' | 'diagram' | 'hybrid';
  layout_hint?: string | null;
  diagram_hint?: DiagramHint | null;
  key_points: string[];
  source_refs?: Array<{ resource_id: string; locator?: string | null }>;
  image_ids: string[];
  intent: string;
}

export interface GlossaryItem {
  term: string;
  short_label: string;
}

export interface PlanContent {
  title: string;
  audience: string;
  goal: string;
  narrative_summary: string;
  glossary: GlossaryItem[];
  slides: PlanSlide[];
}

export interface PlanRecord {
  id: string;
  deck_id: string;
  version: number;
  status: 'draft' | 'approved';
  content: PlanContent;
  created_by: 'ai' | 'user';
  created_at: string;
  updated_at: string;
}

export interface JobRecord {
  id: string;
  deck_id: string;
  slide_id: string | null;
  kind: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
  priority: number;
  progress: Record<string, any>;
  result: Record<string, any> | null;
  attempts: number;
  error: string | null;
  cancel_requested: boolean;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}
