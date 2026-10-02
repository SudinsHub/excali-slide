import { describe, expect, it, vi } from 'vitest';
import { loadSlideForEditor, normalizeSkeleton } from '../excalidraw/normalize';
import { Skeleton, SlideDetail } from '../types';

describe('normalizeSkeleton', () => {
  it('normalizes a cover skeleton into Excalidraw elements with frame first', async () => {
    const skeleton: Skeleton = {
      version: 1,
      frame: { width: 1920, height: 1080 },
      elements: [
        {
          type: 'frame',
          id: 'slide-frame',
          name: 'Cover',
          x: 0,
          y: 0,
          width: 1920,
          height: 1080,
          children: ['title', 'subtitle'],
        },
        {
          type: 'text',
          id: 'title',
          x: 120,
          y: 380,
          width: 1680,
          height: 130,
          text: 'Title Text',
        },
        {
          type: 'text',
          id: 'subtitle',
          x: 120,
          y: 540,
          width: 1680,
          height: 60,
          text: 'Subtitle Text',
        },
      ],
      asset_ids: [],
    };

    const result = await normalizeSkeleton(skeleton);
    expect(result.elements.length).toBeGreaterThanOrEqual(3);

    const frameEl = result.elements.find((e) => e.type === 'frame');
    expect(frameEl).toBeDefined();
    expect(frameEl.id).toBe('slide-frame');
    expect(frameEl.width).toBe(1920);
    expect(frameEl.height).toBe(1080);
  });

  it('normalizes diagram elements with labels and bound arrows', async () => {
    const skeleton: Skeleton = {
      version: 1,
      frame: { width: 1920, height: 1080 },
      elements: [
        {
          type: 'frame',
          id: 'slide-frame',
          name: '',
          x: 0,
          y: 0,
          width: 1920,
          height: 1080,
          children: ['n1', 'n2', 'e1'],
        },
        {
          type: 'rectangle',
          id: 'n1',
          x: 200,
          y: 400,
          width: 250,
          height: 120,
          label: {
            text: 'Step 1\nDetails',
            fontSize: 28,
            strokeColor: '#1e1e1e',
          },
        },
        {
          type: 'rectangle',
          id: 'n2',
          x: 600,
          y: 400,
          width: 250,
          height: 120,
          label: {
            text: 'Step 2',
            fontSize: 28,
          },
        },
        {
          type: 'arrow',
          id: 'e1',
          x: 450,
          y: 460,
          width: 150,
          height: 0,
          start: { id: 'n1' },
          end: { id: 'n2' },
        },
      ],
      asset_ids: [],
    };

    const result = await normalizeSkeleton(skeleton);
    const n1 = result.elements.find((e) => e.id === 'n1');
    const arrow = result.elements.find((e) => e.id === 'e1');

    expect(n1).toBeDefined();
    expect(arrow).toBeDefined();
    expect(arrow.startBinding?.elementId).toBe('n1');
    expect(arrow.endBinding?.elementId).toBe('n2');
  });

  it('preloads image assets via fetchAssetDataUrl and attaches to files map', async () => {
    const mockFetcher = vi.fn().mockResolvedValue('data:image/png;base64,mockpngdata');
    const skeleton: Skeleton = {
      version: 1,
      frame: { width: 1920, height: 1080 },
      elements: [
        {
          type: 'frame',
          id: 'slide-frame',
          name: '',
          x: 0,
          y: 0,
          width: 1920,
          height: 1080,
          children: ['img1'],
        },
        {
          type: 'image',
          id: 'img1',
          fileId: 'mock_sha1_hash',
          x: 100,
          y: 100,
          width: 400,
          height: 300,
        },
      ],
      asset_ids: ['mock_sha1_hash'],
    };

    const result = await normalizeSkeleton(skeleton, mockFetcher);
    expect(mockFetcher).toHaveBeenCalledWith('mock_sha1_hash');
    expect(result.files['mock_sha1_hash']).toBeDefined();
    expect(result.files['mock_sha1_hash'].dataURL).toBe('data:image/png;base64,mockpngdata');
  });
});

describe('loadSlideForEditor priority', () => {
  it('prefers draft scene when available', async () => {
    const slide: SlideDetail = {
      id: 'slide-1',
      deck_id: 'deck-1',
      position: 0,
      plan_key: null,
      status: 'ready',
      error: null,
      current_version: {
        id: 'v1',
        slide_id: 'slide-1',
        seq: 1,
        parent_version_id: null,
        origin: 'manual',
        prompt: null,
        summary: null,
        ir: null,
        skeleton: null,
        scene: { elements: [{ id: 'from_version', type: 'rectangle', x: 0, y: 0 }] },
        scene_hash: 'vh',
        warnings: [],
        created_at: new Date().toISOString(),
      },
      draft: {
        scene: { elements: [{ id: 'from_draft', type: 'rectangle', x: 10, y: 10 }] },
        rev: 2,
        hash: 'dh',
        updated_at: new Date().toISOString(),
      },
      is_dirty: true,
    };

    const res = await loadSlideForEditor(slide);
    expect(res.didNormalize).toBe(false);
    expect(res.scene.elements[0].id).toBe('from_draft');
  });

  it('normalizes skeleton and sets didNormalize true when scene is null', async () => {
    const slide: SlideDetail = {
      id: 'slide-1',
      deck_id: 'deck-1',
      position: 0,
      plan_key: null,
      status: 'ready',
      error: null,
      current_version: {
        id: 'v1',
        slide_id: 'slide-1',
        seq: 1,
        parent_version_id: null,
        origin: 'manual',
        prompt: null,
        summary: null,
        ir: null,
        skeleton: {
          version: 1,
          frame: { width: 1920, height: 1080 },
          elements: [
            {
              type: 'frame',
              id: 'slide-frame',
              name: '',
              x: 0,
              y: 0,
              width: 1920,
              height: 1080,
              children: [],
            },
          ],
          asset_ids: [],
        },
        scene: null,
        scene_hash: null,
        warnings: [],
        created_at: new Date().toISOString(),
      },
      draft: null,
      is_dirty: false,
    };

    const res = await loadSlideForEditor(slide);
    expect(res.didNormalize).toBe(true);
    expect(res.normalizingVersionId).toBe('v1');
    expect(res.scene.elements[0].id).toBe('slide-frame');
  });
});
