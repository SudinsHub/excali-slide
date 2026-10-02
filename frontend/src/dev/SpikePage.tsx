import {
  convertToExcalidrawElements,
  exportToBlob,
  exportToCanvas,
} from '@excalidraw/excalidraw';
import React, { useEffect, useState } from 'react';

export const SpikePage: React.FC = () => {
  const [results, setResults] = useState<Record<string, any>>({});
  const [exportedImageUrl, setExportedImageUrl] = useState<string | null>(null);

  useEffect(() => {
    async function runSpike() {
      const log: Record<string, any> = {};

      // 1. Test convertToExcalidrawElements with frame, children, label, start/end arrows
      const testSkeleton: any[] = [
        {
          type: 'frame',
          id: 'slide-frame',
          name: 'Spike Frame',
          x: 0,
          y: 0,
          width: 1920,
          height: 1080,
          children: ['n1', 'n2', 'arrow1', 'img1'],
        },
        {
          type: 'rectangle',
          id: 'n1',
          x: 200,
          y: 300,
          width: 300,
          height: 150,
          label: {
            text: 'Node 1\nMulti-line Label',
            fontSize: 28,
            strokeColor: '#1e1e1e',
          },
        },
        {
          type: 'rectangle',
          id: 'n2',
          x: 700,
          y: 300,
          width: 300,
          height: 150,
          label: {
            text: 'Node 2',
            fontSize: 28,
          },
        },
        {
          type: 'arrow',
          id: 'arrow1',
          x: 500,
          y: 375,
          width: 200,
          height: 0,
          start: { id: 'n1' },
          end: { id: 'n2' },
        },
        {
          type: 'image',
          id: 'img1',
          fileId: 'mock_file_id',
          x: 1100,
          y: 300,
          width: 200,
          height: 200,
          status: 'saved',
        },
      ];

      try {
        const converted = convertToExcalidrawElements(testSkeleton, { regenerateIds: false });
        log.q1_converted_count = converted.length;
        const frameEl = converted.find((e) => e.type === 'frame');
        const node1 = converted.find((e) => e.id === 'n1');
        const arrow = converted.find((e) => e.id === 'arrow1');
        const image = converted.find((e) => e.id === 'img1');

        log.q1_frame_present = !!frameEl;
        log.q1_node1_width = node1?.width;
        log.q1_node1_height = node1?.height;
        log.q1_bound_arrow_start = (arrow as any)?.startBinding?.elementId === 'n1';
        log.q1_bound_arrow_end = (arrow as any)?.endBinding?.elementId === 'n2';

        // Q2: image skeleton support
        log.q2_image_converted = !!image && (image as any).fileId === 'mock_file_id';

        // Q3: Frame export clipping
        if (frameEl) {
          const canvasScale1 = await exportToCanvas({
            elements: converted,
            appState: { viewBackgroundColor: '#ffffff' },
            files: null,
            exportPadding: 0,
            exportingFrame: frameEl as any,
            getDimensions: () => ({ width: 1920, height: 1080, scale: 1 }),
          });
          log.q3_canvas_scale1_width = canvasScale1.width;
          log.q3_canvas_scale1_height = canvasScale1.height;

          const canvasScale2 = await exportToCanvas({
            elements: converted,
            appState: { viewBackgroundColor: '#ffffff' },
            files: null,
            exportPadding: 0,
            exportingFrame: frameEl as any,
            getDimensions: () => ({ width: 3840, height: 2160, scale: 2 }),
          });
          log.q3_canvas_scale2_width = canvasScale2.width;
          log.q3_canvas_scale2_height = canvasScale2.height;

          const blob = await exportToBlob({
            elements: converted,
            appState: { viewBackgroundColor: '#ffffff' },
            files: null,
            exportPadding: 0,
            exportingFrame: frameEl as any,
            mimeType: 'image/png',
          });
          log.q3_blob_size_bytes = blob.size;
          setExportedImageUrl(URL.createObjectURL(blob));
        }
      } catch (err: any) {
        log.error = err.message || String(err);
      }

      setResults(log);
    }

    runSpike();
  }, []);

  return (
    <div className="p-8 max-w-4xl mx-auto font-sans">
      <h1 className="text-xl font-bold mb-4">Pass 1 Excalidraw Spike Results</h1>
      <pre className="p-4 bg-slate-900 text-emerald-400 rounded-lg text-xs overflow-auto mb-6">
        {JSON.stringify(results, null, 2)}
      </pre>

      {exportedImageUrl && (
        <div>
          <h2 className="text-sm font-bold mb-2">Exported Frame Preview (Clipped to 1920×1080):</h2>
          <img
            src={exportedImageUrl}
            alt="Spike Export"
            className="border rounded shadow-lg max-w-full aspect-video object-contain bg-white"
          />
        </div>
      )}
    </div>
  );
};
