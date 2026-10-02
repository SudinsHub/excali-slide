import { exportToBlob, getNonDeletedElements } from '@excalidraw/excalidraw';
import { loadSlideForEditor } from '../excalidraw/normalize';
import { SlideDetail } from '../types';

export async function renderSlidePng(
  slide: SlideDetail,
  scale: number = 1.0,
  fetchAssetDataUrl?: (id: string) => Promise<string>
): Promise<Blob> {
  const { scene } = await loadSlideForEditor(slide, fetchAssetDataUrl);
  const elements = getNonDeletedElements(scene.elements || []);

  // Locate the frame element
  const frameElement = elements.find(
    (el: any) => el.type === 'frame' || el.id === 'slide-frame'
  );

  return await exportToBlob({
    elements,
    appState: {
      viewBackgroundColor: scene.appState?.viewBackgroundColor || '#ffffff',
      exportWithDarkMode: false,
      exportBackground: true,
    },
    files: scene.files || null,
    exportPadding: 0,
    exportingFrame: frameElement || null,
    getDimensions: (w: number, h: number) => {
      const targetWidth = (frameElement?.width || 1920) * scale;
      const targetHeight = (frameElement?.height || 1080) * scale;
      return {
        width: targetWidth,
        height: targetHeight,
        scale,
      };
    },
    mimeType: 'image/png',
  });
}
