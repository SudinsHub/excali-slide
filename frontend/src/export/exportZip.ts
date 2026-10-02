import JSZip from 'jszip';
import { api } from '../api/client';
import { SlideDetail } from '../types';
import { renderSlidePng } from './renderSlidePng';

export interface ZipExportOptions {
  scale?: number;
  onProgress?: (current: number, total: number) => void;
  isCancelled?: () => boolean;
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'deck';
}

export async function exportDeckToZip(
  slides: SlideDetail[],
  title: string,
  options: ZipExportOptions = {}
): Promise<Blob> {
  const { scale = 1.0, onProgress, isCancelled } = options;

  const zip = new JSZip();
  const padLength = Math.max(2, String(slides.length).length);

  for (let i = 0; i < slides.length; i++) {
    if (isCancelled && isCancelled()) {
      throw new Error('Export cancelled by user');
    }

    if (onProgress) {
      onProgress(i + 1, slides.length);
    }

    const slide = slides[i];
    const pngBlob = await renderSlidePng(slide, scale, api.fetchAssetDataUrl);
    const pngBytes = await pngBlob.arrayBuffer();

    const fileNum = String(i + 1).padStart(padLength, '0');
    const fileName = `slide-${fileNum}.png`;

    zip.file(fileName, pngBytes, { compression: 'STORE' });

    // Macrotask yield to keep browser UI responsive
    await new Promise((resolve) => setTimeout(resolve, 10));
  }

  return await zip.generateAsync({ type: 'blob' });
}
