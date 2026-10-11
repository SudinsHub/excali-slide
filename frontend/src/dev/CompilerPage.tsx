import {
  Excalidraw,
  convertToExcalidrawElements,
} from '@excalidraw/excalidraw';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Deck, SlideLight } from '../types';
import { FIXTURES } from './fixtures';

if (typeof window !== 'undefined') {
  (window as any).EXCALIDRAW_ASSET_PATH = '/';
}

const UI_OPTIONS = {
  canvasActions: {
    changeViewBackgroundColor: true,
    clearCanvas: false,
    loadScene: false,
    saveToActiveFile: false,
    export: false,
    saveAsImage: false,
  },
} as const;

interface QualityIssue {
  code: string;
  path?: string;
  element_id?: string;
  message: string;
  severity: 'warning' | 'error';
}

interface CompileStats {
  node_count?: number;
  element_count?: number;
  min_font_used?: number;
  bbox?: [number, number, number, number];
}

export const CompilerPage: React.FC = () => {
  const [selectedFixtureKey, setSelectedFixtureKey] = useState<string>('cover.json');
  const [jsonText, setJsonText] = useState<string>(
    JSON.stringify(FIXTURES['cover.json'], null, 2)
  );
  const [isCompiling, setIsCompiling] = useState<boolean>(false);
  const [compileErrors, setCompileErrors] = useState<QualityIssue[]>([]);
  const [compileWarnings, setCompileWarnings] = useState<QualityIssue[]>([]);
  const [stats, setStats] = useState<CompileStats | null>(null);
  const [showMarginGrid, setShowMarginGrid] = useState<boolean>(false);
  const [lastCompiledSkeleton, setLastCompiledSkeleton] = useState<any>(null);

  // Excalidraw preview state
  const excalidrawAPIRef = useRef<any>(null);
  const [previewData, setPreviewData] = useState<any>(null);

  // "Apply to slide" dialog state
  const [showApplyModal, setShowApplyModal] = useState<boolean>(false);
  const [decks, setDecks] = useState<Deck[]>([]);
  const [selectedDeckId, setSelectedDeckId] = useState<string>('');
  const [slides, setSlides] = useState<SlideLight[]>([]);
  const [selectedSlideId, setSelectedSlideId] = useState<string>('');
  const [isApplying, setIsApplying] = useState<boolean>(false);
  const [applyFeedback, setApplyFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
    deckId?: string;
  } | null>(null);

  // Compile function
  const executeCompile = useCallback(
    async (irObject: any, skeletonOverrideGrid?: boolean) => {
      setIsCompiling(true);
      try {
        const res = await api.devCompile(irObject);
        setCompileErrors(res.errors || []);
        setCompileWarnings(res.warnings || []);
        setStats(res.stats || null);
        setLastCompiledSkeleton(res.skeleton);

        if (res.skeleton) {
          updateSceneFromSkeleton(
            res.skeleton,
            skeletonOverrideGrid !== undefined ? skeletonOverrideGrid : showMarginGrid
          );
        } else {
          setPreviewData(null);
        }
      } catch (err: any) {
        setCompileErrors([
          {
            code: err.code || 'compile_exception',
            message: err.message || 'Server error compiling IR',
            severity: 'error',
          },
        ]);
        setPreviewData(null);
      } finally {
        setIsCompiling(false);
      }
    },
    [showMarginGrid]
  );

  // Build grid elements to visually assist layout validation
  const buildMarginGridElements = () => {
    return [
      // Safe content margin box: x=120, y=220, w=1680, h=760
      {
        type: 'rectangle',
        id: 'guide-content-margin',
        x: 120,
        y: 220,
        width: 1680,
        height: 760,
        strokeColor: '#3b82f6',
        strokeStyle: 'dashed',
        strokeWidth: 1,
        roughness: 0,
        opacity: 40,
        locked: true,
      },
      // Header region box: x=120, y=80, w=1680, h=120
      {
        type: 'rectangle',
        id: 'guide-header-margin',
        x: 120,
        y: 80,
        width: 1680,
        height: 120,
        strokeColor: '#a855f7',
        strokeStyle: 'dashed',
        strokeWidth: 1,
        roughness: 0,
        opacity: 40,
        locked: true,
      },
      // Center crosshair X
      {
        type: 'line',
        id: 'guide-crosshair-v',
        x: 960,
        y: 80,
        width: 0,
        height: 900,
        points: [
          [0, 0],
          [0, 900],
        ],
        strokeColor: '#ef4444',
        strokeStyle: 'dotted',
        strokeWidth: 1,
        roughness: 0,
        opacity: 30,
        locked: true,
      },
      // Center crosshair Y
      {
        type: 'line',
        id: 'guide-crosshair-h',
        x: 120,
        y: 540,
        width: 1680,
        height: 0,
        points: [
          [0, 0],
          [1680, 0],
        ],
        strokeColor: '#ef4444',
        strokeStyle: 'dotted',
        strokeWidth: 1,
        roughness: 0,
        opacity: 30,
        locked: true,
      },
    ];
  };

  const updateSceneFromSkeleton = (skeleton: any, withGrid: boolean) => {
    let elements = [...(skeleton.elements || [])];

    if (withGrid) {
      const gridElements = buildMarginGridElements();
      // Ensure frame includes guide children so Excalidraw clips/groups appropriately
      const frameEl = elements.find((el: any) => el.type === 'frame' || el.id === 'slide-frame');
      if (frameEl && Array.isArray(frameEl.children)) {
        frameEl.children = [...frameEl.children, ...gridElements.map((g) => g.id)];
      }
      elements = [...elements, ...gridElements];
    }

    const converted = convertToExcalidrawElements(elements, { regenerateIds: false });
    const scene = {
      elements: converted,
      appState: { viewBackgroundColor: '#ffffff' },
    };

    setPreviewData(scene);

    if (excalidrawAPIRef.current) {
      excalidrawAPIRef.current.updateScene(scene);
      setTimeout(() => {
        fitCanvasToFrame();
      }, 50);
    }
  };

  const fitCanvasToFrame = () => {
    const api = excalidrawAPIRef.current;
    if (!api) return;
    const elements = api.getSceneElements();
    const frame = elements.find((el: any) => el.type === 'frame' || el.id === 'slide-frame');
    if (frame) {
      api.scrollToContent(frame, {
        fitToViewport: true,
        viewportZoomFactor: 0.88,
        animate: false,
      });
    }
  };

  // Compile initial fixture on mount
  useEffect(() => {
    try {
      const parsed = JSON.parse(jsonText);
      executeCompile(parsed);
    } catch {
      // ignore
    }
  }, []);

  // When fixture dropdown changes
  const handleSelectFixture = (key: string) => {
    setSelectedFixtureKey(key);
    const fixtureData = FIXTURES[key];
    if (fixtureData) {
      const formatted = JSON.stringify(fixtureData, null, 2);
      setJsonText(formatted);
      executeCompile(fixtureData);
    }
  };

  // Format JSON button
  const handleFormatJson = () => {
    try {
      const parsed = JSON.parse(jsonText);
      setJsonText(JSON.stringify(parsed, null, 2));
    } catch (e: any) {
      alert(`Invalid JSON: ${e.message}`);
    }
  };

  // Manual compile button
  const handleManualCompile = () => {
    try {
      const parsed = JSON.parse(jsonText);
      executeCompile(parsed);
    } catch (e: any) {
      setCompileErrors([
        {
          code: 'json_syntax_error',
          message: `JSON syntax error: ${e.message}`,
          severity: 'error',
        },
      ]);
      setPreviewData(null);
    }
  };

  // Toggle Grid
  const handleToggleGrid = () => {
    const nextVal = !showMarginGrid;
    setShowMarginGrid(nextVal);
    if (lastCompiledSkeleton) {
      updateSceneFromSkeleton(lastCompiledSkeleton, nextVal);
    }
  };

  // Handle Apply to Slide modal
  const handleOpenApplyModal = async () => {
    setShowApplyModal(true);
    setApplyFeedback(null);
    try {
      const deckList = await api.getDecks();
      setDecks(deckList);
      if (deckList.length > 0) {
        setSelectedDeckId(deckList[0].id);
        const slideList = await api.getSlides(deckList[0].id);
        setSlides(slideList);
        if (slideList.length > 0) {
          setSelectedSlideId(slideList[0].id);
        }
      }
    } catch (err: any) {
      setApplyFeedback({
        type: 'error',
        message: `Failed to load decks: ${err.message}`,
      });
    }
  };

  const handleDeckChange = async (deckId: string) => {
    setSelectedDeckId(deckId);
    setSelectedSlideId('');
    try {
      const slideList = await api.getSlides(deckId);
      setSlides(slideList);
      if (slideList.length > 0) {
        setSelectedSlideId(slideList[0].id);
      }
    } catch (err: any) {
      setApplyFeedback({
        type: 'error',
        message: `Failed to load slides: ${err.message}`,
      });
    }
  };

  const handleConfirmApply = async () => {
    if (!selectedSlideId) return;
    setIsApplying(true);
    setApplyFeedback(null);
    try {
      const parsed = JSON.parse(jsonText);
      await api.devApplyIR(selectedSlideId, parsed);
      setApplyFeedback({
        type: 'success',
        message: 'IR successfully compiled and applied to slide version!',
        deckId: selectedDeckId,
      });
    } catch (err: any) {
      setApplyFeedback({
        type: 'error',
        message: `Error applying IR: ${err.message}`,
      });
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-900 text-slate-100 overflow-hidden font-sans">
      {/* Top Header */}
      <header className="h-14 border-b border-slate-800 bg-slate-950 px-5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
          >
            <svg
              className="w-5 h-5 text-indigo-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            <span className="text-sm font-semibold text-white">Back to Decks</span>
          </Link>
          <span className="text-slate-700">|</span>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-900/60 text-indigo-300 border border-indigo-700/50">
              Dev Tools
            </span>
            <h1 className="text-sm font-semibold text-slate-200">
              IR Compiler Playground (Pass 2)
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/dev/calibrate"
            className="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
          >
            Font Calibrator
          </Link>
          <button
            onClick={handleOpenApplyModal}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition flex items-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
              />
            </svg>
            Apply to Slide...
          </button>
        </div>
      </header>

      {/* Main Two-Column Layout */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Left Column: JSON Editor */}
        <div className="w-1/2 flex flex-col border-r border-slate-800 bg-slate-900/50">
          {/* Controls Bar */}
          <div className="h-12 border-b border-slate-800 px-4 flex items-center justify-between bg-slate-900 shrink-0">
            <div className="flex items-center gap-2">
              <label className="text-xs font-medium text-slate-400">Fixture:</label>
              <select
                value={selectedFixtureKey}
                onChange={(e) => handleSelectFixture(e.target.value)}
                className="bg-slate-800 text-slate-200 text-xs rounded border border-slate-700 px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                {Object.keys(FIXTURES).map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleFormatJson}
                className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                title="Format JSON"
              >
                Format
              </button>
              <button
                onClick={handleManualCompile}
                disabled={isCompiling}
                className="px-3 py-1 text-xs font-semibold rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition flex items-center gap-1.5"
              >
                {isCompiling ? (
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                )}
                Compile IR
              </button>
            </div>
          </div>

          {/* Editor Area */}
          <div className="flex-1 relative p-3 overflow-hidden flex flex-col">
            <textarea
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
              spellCheck={false}
              className="w-full flex-1 bg-slate-950 font-mono text-xs text-slate-200 p-3.5 rounded-lg border border-slate-800 resize-none focus:outline-none focus:border-indigo-500 leading-relaxed overflow-y-auto selection:bg-indigo-500/30"
              placeholder="Paste SlideIR JSON here..."
            />
          </div>
        </div>

        {/* Right Column: Live Excalidraw Preview + Quality Gate + Stats */}
        <div className="w-1/2 flex flex-col bg-slate-950 min-h-0">
          {/* Preview Toolbar & Stats */}
          <div className="h-12 border-b border-slate-800 px-4 flex items-center justify-between bg-slate-900 shrink-0">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-slate-300">Live Preview</span>
              <button
                onClick={handleToggleGrid}
                className={`px-2.5 py-1 text-xs rounded border transition flex items-center gap-1.5 ${
                  showMarginGrid
                    ? 'bg-indigo-950/80 border-indigo-500 text-indigo-300 font-semibold'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
                }`}
                title="Toggle visual margin and safe zone guides"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16m-7 6h7"
                  />
                </svg>
                Margin Grid
              </button>
              <button
                onClick={fitCanvasToFrame}
                className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition"
                title="Fit frame in viewport"
              >
                Fit Zoom
              </button>
            </div>

            {/* Stats Badges */}
            {stats && (
              <div className="flex items-center gap-2 text-xs">
                <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  Nodes: <strong className="text-white">{stats.node_count ?? 0}</strong>
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  Elements: <strong className="text-white">{stats.element_count ?? 0}</strong>
                </span>
                <span
                  className={`px-2 py-0.5 rounded border ${
                    (stats.min_font_used || 24) >= 24
                      ? 'bg-emerald-950/70 border-emerald-700/60 text-emerald-300'
                      : 'bg-rose-950/70 border-rose-700/60 text-rose-300'
                  }`}
                >
                  Min Font: <strong>{stats.min_font_used ?? 24}px</strong>
                </span>
              </div>
            )}
          </div>

          {/* Excalidraw Canvas Container */}
          <div className="flex-1 relative bg-slate-900 min-h-0">
            {previewData ? (
              <Excalidraw
                excalidrawAPI={(api) => {
                  excalidrawAPIRef.current = api;
                  fitCanvasToFrame();
                }}
                initialData={previewData}
                UIOptions={UI_OPTIONS}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-slate-500 text-sm">
                {compileErrors.length > 0
                  ? 'Compilation failed. See errors below.'
                  : 'No skeleton available.'}
              </div>
            )}
          </div>

          {/* Bottom Panel: Quality Gate Issues & Bounding Box */}
          <div className="h-44 border-t border-slate-800 bg-slate-900/90 flex flex-col shrink-0">
            <div className="h-8 px-4 border-b border-slate-800 flex items-center justify-between text-xs">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-slate-300">Quality Gate Diagnostics</span>
                {compileErrors.length === 0 && compileWarnings.length === 0 ? (
                  <span className="inline-flex items-center gap-1 text-emerald-400 text-[11px] font-medium">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Clean (0 issues)
                  </span>
                ) : (
                  <div className="flex items-center gap-2">
                    {compileErrors.length > 0 && (
                      <span className="text-rose-400 font-semibold text-[11px]">
                        {compileErrors.length} Error{compileErrors.length > 1 ? 's' : ''}
                      </span>
                    )}
                    {compileWarnings.length > 0 && (
                      <span className="text-amber-400 font-semibold text-[11px]">
                        {compileWarnings.length} Warning{compileWarnings.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {stats?.bbox && (
                <span className="text-slate-400 text-[11px] font-mono">
                  BBox: [{stats.bbox.map((v) => Math.round(v)).join(', ')}] (
                  {Math.round(stats.bbox[2] - stats.bbox[0])} ×{' '}
                  {Math.round(stats.bbox[3] - stats.bbox[1])} px)
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-2.5 space-y-1.5 font-mono text-xs">
              {compileErrors.map((err, idx) => (
                <div
                  key={`err-${idx}`}
                  className="px-3 py-1.5 rounded bg-rose-950/60 border border-rose-800/60 text-rose-200 flex items-start gap-2"
                >
                  <span className="shrink-0 px-1 py-0.2 rounded bg-rose-900 text-rose-300 text-[10px] uppercase font-bold">
                    ERR
                  </span>
                  <span className="text-rose-400 font-bold">{err.code}</span>
                  {(err.path || err.element_id) && (
                    <span className="text-rose-300/70">
                      [{err.path || err.element_id}]
                    </span>
                  )}
                  <span className="text-slate-200 flex-1">{err.message}</span>
                </div>
              ))}

              {compileWarnings.map((warn, idx) => (
                <div
                  key={`warn-${idx}`}
                  className="px-3 py-1.5 rounded bg-amber-950/50 border border-amber-800/50 text-amber-200 flex items-start gap-2"
                >
                  <span className="shrink-0 px-1 py-0.2 rounded bg-amber-900 text-amber-300 text-[10px] uppercase font-bold">
                    WARN
                  </span>
                  <span className="text-amber-400 font-bold">{warn.code}</span>
                  {(warn.path || warn.element_id) && (
                    <span className="text-amber-300/70">
                      [{warn.path || warn.element_id}]
                    </span>
                  )}
                  <span className="text-slate-200 flex-1">{warn.message}</span>
                </div>
              ))}

              {compileErrors.length === 0 && compileWarnings.length === 0 && (
                <div className="h-full flex items-center justify-center text-slate-500 italic text-xs">
                  No layout or density issues detected by quality gate.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* "Apply to Slide" Modal */}
      {showApplyModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md p-5 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white">Apply IR to Slide</h3>
              <button
                onClick={() => setShowApplyModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold cursor-pointer"
              >
                &times;
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              This will validate and compile the current IR, clear any existing draft, and save a
              new version (origin = <code className="text-indigo-300">manual</code>) on the chosen
              slide.
            </p>

            {applyFeedback && (
              <div
                className={`p-3 rounded-lg text-xs ${
                  applyFeedback.type === 'success'
                    ? 'bg-emerald-950/80 border border-emerald-700 text-emerald-200'
                    : 'bg-rose-950/80 border border-rose-700 text-rose-200'
                }`}
              >
                {applyFeedback.message}
                {applyFeedback.deckId && (
                  <div className="mt-2">
                    <Link
                      to={`/decks/${applyFeedback.deckId}`}
                      className="underline font-bold text-indigo-300 hover:text-white"
                    >
                      Open in Deck Workspace &rarr;
                    </Link>
                  </div>
                )}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Deck
                </label>
                <select
                  value={selectedDeckId}
                  onChange={(e) => handleDeckChange(e.target.value)}
                  className="w-full bg-slate-800 text-slate-200 text-xs rounded-lg border border-slate-700 p-2.5 focus:outline-none focus:border-indigo-500"
                >
                  {decks.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title} ({d.id.substring(0, 8)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Slide
                </label>
                <select
                  value={selectedSlideId}
                  onChange={(e) => setSelectedSlideId(e.target.value)}
                  disabled={slides.length === 0}
                  className="w-full bg-slate-800 text-slate-200 text-xs rounded-lg border border-slate-700 p-2.5 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                >
                  {slides.map((s) => (
                    <option key={s.id} value={s.id}>
                      Slide #{s.position + 1} ({s.id.substring(0, 8)})
                    </option>
                  ))}
                  {slides.length === 0 && <option>No slides available</option>}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowApplyModal(false)}
                className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Close
              </button>
              <button
                onClick={handleConfirmApply}
                disabled={isApplying || !selectedSlideId}
                className="px-4 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white transition flex items-center gap-1.5"
              >
                {isApplying ? 'Applying...' : 'Apply IR'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default CompilerPage;
