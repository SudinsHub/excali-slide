import { convertToExcalidrawElements } from '@excalidraw/excalidraw';
import { ExcalidrawScene, Skeleton, SlideDetail } from '../types';

export interface NormalizedResult {
  elements: any[];
  files: Record<string, any>;
}

export async function normalizeSkeleton(
  skeleton: Skeleton,
  fetchAssetDataUrl?: (id: string) => Promise<string>
): Promise<NormalizedResult> {
  const files: Record<string, any> = {};

  // Extract all asset/file IDs from skeleton
  const assetIds = new Set<string>(skeleton.asset_ids || []);
  for (const el of skeleton.elements || []) {
    if (el.type === 'image' && el.fileId) {
      assetIds.add(el.fileId);
    }
  }

  // Load asset dataURLs if fetcher provided
  if (fetchAssetDataUrl && assetIds.size > 0) {
    await Promise.all(
      Array.from(assetIds).map(async (fileId) => {
        try {
          const dataUrl = await fetchAssetDataUrl(fileId);
          files[fileId] = {
            id: fileId,
            dataURL: dataUrl,
            mimeType: dataUrl.startsWith('data:image/svg+xml') ? 'image/svg+xml' : 'image/png',
            created: Date.now(),
          };
        } catch (err) {
          console.warn(`Failed to preload asset ${fileId} during normalization:`, err);
        }
      })
    );
  }

  // Convert using Excalidraw's convertToExcalidrawElements
  const converted = convertToExcalidrawElements(skeleton.elements as any, {
    regenerateIds: false,
  });

  return {
    elements: converted,
    files,
  };
}

export interface SlideLoadResult {
  scene: ExcalidrawScene;
  didNormalize: boolean;
  normalizingVersionId: string | null;
}

export async function loadSlideForEditor(
  slide: SlideDetail,
  fetchAssetDataUrl?: (id: string) => Promise<string>
): Promise<SlideLoadResult> {
  // 1. If draft scene exists and has elements, use it
  if (slide.draft?.scene && Array.isArray(slide.draft.scene.elements) && slide.draft.scene.elements.length > 0) {
    return {
      scene: {
        elements: slide.draft.scene.elements,
        appState: slide.draft.scene.appState || { viewBackgroundColor: '#ffffff' },
        files: slide.draft.scene.files || {},
      },
      didNormalize: false,
      normalizingVersionId: null,
    };
  }

  // 2. If current version has a normalized scene, use it
  if (
    slide.current_version?.scene &&
    Array.isArray(slide.current_version.scene.elements) &&
    slide.current_version.scene.elements.length > 0
  ) {
    return {
      scene: {
        elements: slide.current_version.scene.elements,
        appState: slide.current_version.scene.appState || { viewBackgroundColor: '#ffffff' },
        files: slide.current_version.scene.files || {},
      },
      didNormalize: false,
      normalizingVersionId: null,
    };
  }

  // 3. Otherwise, normalize the current version's skeleton
  if (slide.current_version?.skeleton) {
    const { elements, files } = await normalizeSkeleton(
      slide.current_version.skeleton,
      fetchAssetDataUrl
    );
    return {
      scene: {
        elements,
        appState: { viewBackgroundColor: '#ffffff' },
        files,
      },
      didNormalize: true,
      normalizingVersionId: slide.current_version.id,
    };
  }

  // 4. Fallback blank frame scene
  const blankConverted = convertToExcalidrawElements(
    [
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
    ] as any,
    { regenerateIds: false }
  );

  return {
    scene: {
      elements: blankConverted,
      appState: { viewBackgroundColor: '#ffffff' },
      files: {},
    },
    didNormalize: false,
    normalizingVersionId: null,
  };
}
