import React, { useEffect, useState } from 'react';
import { convertToExcalidrawElements } from '@excalidraw/excalidraw';

const SAMPLE_TEXTS = [
  'Modern Cloud Architecture',
  'Microservices & Distributed Systems',
  'Simplicity is prerequisite for reliability.',
  'Data Ingestion Pipeline',
  'Tiered Security Architecture',
  'Continuous Delivery Lifecycle',
  'Engineering Roadmap 2026',
  'Zero Trust Security Model',
  'Quick brown fox jumps over the lazy dog',
  'High Availability & Disaster Recovery',
  'API Gateway and Service Mesh Mesh Networking',
  'Event-Driven Processing Architecture',
  'Database Replication and Sharding Strategies',
  'Observability, Tracing, Metrics, and Alerts',
  'Deploy to Kubernetes Cluster with Helm',
  'PostgreSQL Relational Storage Engine',
  'FastAPI Async Python REST Backend',
  'React 18 Concurrent Rendering Framework',
  'Interactive Canvas with Vector Geometry Math',
  'Excalidraw Slide Studio Portfolio Presentation',
];

const FONT_SIZES = [24, 28, 36, 64];

interface CalibrateResult {
  text: string;
  fontSize: number;
  chars: number;
  measuredWidth: number;
  ratio: number;
}

export const CalibratePage: React.FC = () => {
  const [results, setResults] = useState<CalibrateResult[]>([]);
  const [meanRatio, setMeanRatio] = useState<number>(0);
  const [maxRatio, setMaxRatio] = useState<number>(0);

  useEffect(() => {
    runCalibration();
  }, []);

  const runCalibration = () => {
    const rawSkeletons: any[] = [];
    let idCounter = 0;

    for (const text of SAMPLE_TEXTS) {
      for (const fontSize of FONT_SIZES) {
        idCounter++;
        rawSkeletons.push({
          type: 'text',
          id: `sample_${idCounter}`,
          text,
          fontSize,
          x: 0,
          y: 0,
          width: 0,
          height: 0,
        });
      }
    }

    const converted = convertToExcalidrawElements(rawSkeletons, { regenerateIds: false });
    const computed: CalibrateResult[] = [];

    for (let i = 0; i < rawSkeletons.length; i++) {
      const orig = rawSkeletons[i];
      const conv = converted[i];
      const chars = orig.text.length;
      const width = conv.width || 0;
      const ratio = width > 0 && chars > 0 ? width / (chars * orig.fontSize) : 0;

      computed.push({
        text: orig.text,
        fontSize: orig.fontSize,
        chars,
        measuredWidth: Math.round(width * 10) / 10,
        ratio: Math.round(ratio * 1000) / 1000,
      });
    }

    const validRatios = computed.map((r) => r.ratio).filter((r) => r > 0);
    const mean = validRatios.length > 0 ? validRatios.reduce((a, b) => a + b, 0) / validRatios.length : 0.58;
    const max = validRatios.length > 0 ? Math.max(...validRatios) : 0.65;

    setResults(computed);
    setMeanRatio(Math.round(mean * 1000) / 1000);
    setMaxRatio(Math.round(max * 1000) / 1000);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between pb-6 border-b border-slate-700">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white">Excalidraw Font Calibration</h1>
            <p className="text-slate-400 mt-1">
              Measures real Virgil font advances via <code className="text-amber-400">convertToExcalidrawElements</code>
            </p>
          </div>
          <button
            onClick={runCalibration}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-medium shadow transition"
          >
            Re-run Calibration
          </button>
        </div>

        {/* Metrics Summary */}
        <div className="grid grid-cols-3 gap-6 my-8">
          <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
            <div className="text-sm font-medium text-slate-400">Mean Advance Ratio</div>
            <div className="text-4xl font-extrabold text-indigo-400 mt-2">{meanRatio.toFixed(3)}</div>
            <div className="text-xs text-slate-500 mt-1">width / (chars × fontSize)</div>
          </div>
          <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
            <div className="text-sm font-medium text-slate-400">Recommended CHAR_W (Mean + 5%)</div>
            <div className="text-4xl font-extrabold text-emerald-400 mt-2">
              {(meanRatio > 0 ? Math.round(meanRatio * 1.05 * 100) / 100 : 0.58).toFixed(2)}
            </div>
            <div className="text-xs text-slate-500 mt-1">Safety buffer for hand-drawn font irregularity</div>
          </div>
          <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
            <div className="text-sm font-medium text-slate-400">Maximum Ratio Sample</div>
            <div className="text-4xl font-extrabold text-amber-400 mt-2">{maxRatio.toFixed(3)}</div>
            <div className="text-xs text-slate-500 mt-1">Upper bound character width</div>
          </div>
        </div>

        {/* Samples Table */}
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden shadow">
          <div className="px-6 py-4 border-b border-slate-700 font-semibold text-slate-200">
            Sample Measurements ({results.length} runs)
          </div>
          <div className="max-h-[500px] overflow-y-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/60 sticky top-0 text-slate-400 uppercase text-xs">
                <tr>
                  <th className="py-3 px-4">Sample Text</th>
                  <th className="py-3 px-4">Font Size</th>
                  <th className="py-3 px-4">Chars</th>
                  <th className="py-3 px-4">Width (px)</th>
                  <th className="py-3 px-4">Ratio (w / c·fs)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {results.map((r, i) => (
                  <tr key={i} className="hover:bg-slate-700/30">
                    <td className="py-2.5 px-4 font-mono text-xs text-slate-200">{r.text}</td>
                    <td className="py-2.5 px-4">{r.fontSize}px</td>
                    <td className="py-2.5 px-4">{r.chars}</td>
                    <td className="py-2.5 px-4 font-mono">{r.measuredWidth}</td>
                    <td className="py-2.5 px-4 font-mono font-semibold text-indigo-300">{r.ratio.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
