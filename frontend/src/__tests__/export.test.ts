import JSZip from 'jszip';
import { PDFDocument } from 'pdf-lib';
import { describe, expect, it, vi } from 'vitest';
import * as renderModule from '../export/renderSlidePng';
import { exportDeckToPdf } from '../export/exportPdf';
import { exportDeckToZip, slugify } from '../export/exportZip';
import { SlideDetail } from '../types';

// Mock 1x1 PNG blob
const mockPngBlob = new Blob(
  [
    new Uint8Array([
      0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44,
      0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x06, 0x00, 0x00, 0x00, 0x1f,
      0x15, 0xc4, 0x89, 0x00, 0x00, 0x00, 0x0d, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9c, 0x63, 0x60,
      0x00, 0x00, 0x00, 0x02, 0x00, 0x01, 0x48, 0xaf, 0xa4, 0x71, 0x00, 0x00, 0x00, 0x00, 0x49,
      0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
    ]),
  ],
  { type: 'image/png' }
);

function createMockSlide(id: string, position: number): SlideDetail {
  return {
    id,
    deck_id: 'deck-1',
    position,
    plan_key: null,
    status: 'ready',
    error: null,
    current_version: null,
    draft: null,
    is_dirty: false,
  };
}

describe('slugify', () => {
  it('formats titles into clean URL and filename slugs', () => {
    expect(slugify('My Pitch Deck 2026!')).toBe('my-pitch-deck-2026');
    expect(slugify('  Spaced  Out  Name  ')).toBe('spaced-out-name');
    expect(slugify('### Special @#$ Characters')).toBe('special-characters');
    expect(slugify('')).toBe('deck');
  });
});

describe('exportDeckToZip', () => {
  it('creates a ZIP with zero-padded sequential PNG slide filenames', async () => {
    vi.spyOn(renderModule, 'renderSlidePng').mockResolvedValue(mockPngBlob);

    const slides = [
      createMockSlide('s1', 0),
      createMockSlide('s2', 1),
      createMockSlide('s3', 2),
    ];

    const progressReports: number[] = [];
    const zipBlob = await exportDeckToZip(slides, 'Demo Deck', {
      scale: 1.0,
      onProgress: (cur) => progressReports.push(cur),
    });

    expect(zipBlob.type).toBe('application/zip');
    expect(progressReports).toEqual([1, 2, 3]);

    const zip = await JSZip.loadAsync(zipBlob);
    const filenames = Object.keys(zip.files).sort();
    expect(filenames).toEqual(['slide-01.png', 'slide-02.png', 'slide-03.png']);
  });
});

describe('exportDeckToPdf', () => {
  it('generates a PDF with the exact page count matching slide count', async () => {
    vi.spyOn(renderModule, 'renderSlidePng').mockResolvedValue(mockPngBlob);

    const slides = [
      createMockSlide('s1', 0),
      createMockSlide('s2', 1),
    ];

    const pdfBlob = await exportDeckToPdf(slides, 'Demo Presentation');
    expect(pdfBlob.type).toBe('application/pdf');

    const pdfBytes = await pdfBlob.arrayBuffer();
    const loadedDoc = await PDFDocument.load(pdfBytes);
    expect(loadedDoc.getPageCount()).toBe(2);
    expect(loadedDoc.getTitle()).toBe('Demo Presentation');
  });
});
