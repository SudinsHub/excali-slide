import { PDFDocument } from 'pdf-lib';
import { api } from '../api/client';
import { SlideDetail } from '../types';
import { renderSlidePng } from './renderSlidePng';

export interface PdfExportOptions {
  quality?: 'standard' | 'high';
  onProgress?: (current: number, total: number) => void;
  isCancelled?: () => boolean;
}

export async function exportDeckToPdf(
  slides: SlideDetail[],
  title: string,
  options: PdfExportOptions = {}
): Promise<Blob> {
  const { quality = 'high', onProgress, isCancelled } = options;
  const scale = quality === 'high' ? 2.0 : 1.5;

  const pdfDoc = await PDFDocument.create();
  pdfDoc.setTitle(title);

  // 960 x 540 pt (16:9 ratio)
  const pageWidth = 960;
  const pageHeight = 540;

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

    const embeddedPng = await pdfDoc.embedPng(pngBytes);
    const page = pdfDoc.addPage([pageWidth, pageHeight]);
    page.drawImage(embeddedPng, {
      x: 0,
      y: 0,
      width: pageWidth,
      height: pageHeight,
    });

    // Macrotask yield to keep browser UI responsive
    await new Promise((resolve) => setTimeout(resolve, 10));
  }

  const pdfBytes = await pdfDoc.save();
  return new Blob([new Uint8Array(pdfBytes)], { type: 'application/pdf' });
}
