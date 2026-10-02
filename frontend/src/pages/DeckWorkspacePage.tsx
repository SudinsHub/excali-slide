import {
  ArrowLeft,
  Download,
  FileArchive,
  FileText,
  Play,
} from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { RightPanel } from '../components/RightPanel';
import { SaveStateIndicator } from '../components/SaveStateIndicator';
import { ThumbnailsRail } from '../components/ThumbnailsRail';
import { ExcalidrawEditor } from '../excalidraw/ExcalidrawEditor';
import { exportDeckToPdf } from '../export/exportPdf';
import { exportDeckToZip, slugify } from '../export/exportZip';
import { useDeckStore } from '../store/deckStore';
import { SlideDetail } from '../types';

export const DeckWorkspacePage: React.FC = () => {
  const { id: deckId } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const {
    currentDeck,
    slides,
    activeSlideId,
    activeSlideDetail,
    saveStatus,
    errorMessage,
    fetchDeckAndSlides,
    selectSlide,
    setCurrentDeck,
  } = useDeckStore();

  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [deckTitle, setDeckTitle] = useState('');

  // Export progress modal state
  const [isExporting, setIsExporting] = useState(false);
  const [exportType, setExportType] = useState<'pdf' | 'zip' | null>(null);
  const [exportProgress, setExportProgress] = useState<{ current: number; total: number }>({
    current: 0,
    total: 0,
  });
  const cancelExportRef = useRef(false);

  // Initial load
  useEffect(() => {
    if (deckId) {
      fetchDeckAndSlides(deckId);
    }
  }, [deckId]);

  // Keep deck title in sync
  useEffect(() => {
    if (currentDeck) {
      setDeckTitle(currentDeck.title);
    }
  }, [currentDeck]);

  // Handle slide selection based on URL search query or default to first slide
  useEffect(() => {
    if (slides.length === 0) return;

    const querySlideId = searchParams.get('slide');
    if (querySlideId && slides.some((s) => s.id === querySlideId)) {
      if (activeSlideId !== querySlideId) {
        selectSlide(querySlideId);
      }
    } else {
      // Pick first slide
      const firstSlide = slides[0];
      selectSlide(firstSlide.id);
      setSearchParams({ slide: firstSlide.id }, { replace: true });
    }
  }, [slides]);

  // Update query param when active slide changes
  useEffect(() => {
    if (activeSlideId && searchParams.get('slide') !== activeSlideId) {
      setSearchParams({ slide: activeSlideId }, { replace: true });
    }
  }, [activeSlideId]);

  // Keyboard navigation Alt+Up / Alt+Down between slides
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input or textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      if (e.altKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
        e.preventDefault();
        const currentIdx = slides.findIndex((s) => s.id === activeSlideId);
        if (currentIdx === -1) return;

        let nextIdx = currentIdx;
        if (e.key === 'ArrowUp' && currentIdx > 0) {
          nextIdx = currentIdx - 1;
        } else if (e.key === 'ArrowDown' && currentIdx < slides.length - 1) {
          nextIdx = currentIdx + 1;
        }

        if (nextIdx !== currentIdx) {
          selectSlide(slides[nextIdx].id);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [slides, activeSlideId]);

  const handleTitleSubmit = async () => {
    if (!currentDeck || !deckTitle.trim()) return;
    setIsEditingTitle(false);
    if (deckTitle.trim() !== currentDeck.title) {
      try {
        const updated = await api.updateDeck(currentDeck.id, { title: deckTitle.trim() });
        setCurrentDeck(updated);
      } catch (err: any) {
        alert(err.message || 'Failed to update title');
      }
    }
  };

  const handlePresent = () => {
    if (!currentDeck) return;
    const startSlide = activeSlideId || (slides[0]?.id ?? '');
    navigate(`/present/${currentDeck.id}?slide=${startSlide}`);
  };

  const handleExportPdf = async (quality: 'standard' | 'high' = 'high') => {
    if (!currentDeck || slides.length === 0) return;
    setIsExporting(true);
    setExportType('pdf');
    setExportProgress({ current: 0, total: slides.length });
    cancelExportRef.current = false;

    try {
      // 1. Fetch details of all slides
      const fullSlides: SlideDetail[] = [];
      for (const s of slides) {
        const detail = await api.getSlide(s.id);
        fullSlides.push(detail);
      }

      // 2. Generate PDF
      const blob = await exportDeckToPdf(fullSlides, currentDeck.title, {
        quality,
        onProgress: (cur, tot) => setExportProgress({ current: cur, total: tot }),
        isCancelled: () => cancelExportRef.current,
      });

      // 3. Download
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${slugify(currentDeck.title)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      if (err.message !== 'Export cancelled by user') {
        alert(err.message || 'Export PDF failed');
      }
    } finally {
      setIsExporting(false);
      setExportType(null);
    }
  };

  const handleExportZip = async () => {
    if (!currentDeck || slides.length === 0) return;
    setIsExporting(true);
    setExportType('zip');
    setExportProgress({ current: 0, total: slides.length });
    cancelExportRef.current = false;

    try {
      const fullSlides: SlideDetail[] = [];
      for (const s of slides) {
        const detail = await api.getSlide(s.id);
        fullSlides.push(detail);
      }

      const blob = await exportDeckToZip(fullSlides, currentDeck.title, {
        scale: 1.0,
        onProgress: (cur, tot) => setExportProgress({ current: cur, total: tot }),
        isCancelled: () => cancelExportRef.current,
      });

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${slugify(currentDeck.title)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      if (err.message !== 'Export cancelled by user') {
        alert(err.message || 'Export ZIP failed');
      }
    } finally {
      setIsExporting(false);
      setExportType(null);
    }
  };

  if (!currentDeck) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50">
        <div className="text-xs text-slate-500">Loading workspace...</div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-slate-100 overflow-hidden">
      {/* Top Header */}
      <header className="h-14 border-b border-slate-200 bg-white px-4 flex items-center justify-between z-10">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
            title="Back to decks"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          {/* Editable Title */}
          {isEditingTitle ? (
            <input
              type="text"
              value={deckTitle}
              autoFocus
              onChange={(e) => setDeckTitle(e.target.value)}
              onBlur={handleTitleSubmit}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleTitleSubmit();
                if (e.key === 'Escape') setIsEditingTitle(false);
              }}
              className="text-sm font-bold text-slate-900 px-2 py-1 border border-brand-500 rounded outline-none"
            />
          ) : (
            <div
              onClick={() => setIsEditingTitle(true)}
              className="text-sm font-bold text-slate-900 hover:bg-slate-100 px-2 py-1 rounded cursor-pointer transition-colors truncate max-w-sm"
              title="Click to rename deck"
            >
              {currentDeck.title}
            </div>
          )}

          {/* Workflow Steps Indicator */}
          <div className="hidden md:flex items-center gap-1.5 ml-4 pl-4 border-l border-slate-200 text-xs">
            <span className="text-slate-400 font-medium px-2 py-0.5 rounded cursor-not-allowed">
              1. Brief
            </span>
            <span className="text-slate-300">›</span>
            <span className="text-slate-400 font-medium px-2 py-0.5 rounded cursor-not-allowed">
              2. Plan
            </span>
            <span className="text-slate-300">›</span>
            <span className="bg-brand-50 text-brand-700 font-semibold px-2 py-0.5 rounded border border-brand-200">
              3. Slides
            </span>
          </div>
        </div>

        {/* Right Action Tools */}
        <div className="flex items-center gap-2.5">
          <SaveStateIndicator
            status={saveStatus}
            errorMessage={errorMessage}
            onRetry={() => {
              if (activeSlideId) selectSlide(activeSlideId);
            }}
          />

          <div className="h-4 w-px bg-slate-200 mx-1" />

          {/* Export PDF */}
          <button
            onClick={() => handleExportPdf('high')}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            title="Export deck to PDF"
          >
            <FileText className="w-3.5 h-3.5 text-slate-500" />
            <span>PDF</span>
          </button>

          {/* Export ZIP */}
          <button
            onClick={handleExportZip}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            title="Export high-res slide PNGs in a ZIP"
          >
            <FileArchive className="w-3.5 h-3.5 text-slate-500" />
            <span>ZIP</span>
          </button>

          {/* Present Mode Button */}
          <button
            onClick={handlePresent}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Present</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Thumbnails Rail */}
        <ThumbnailsRail />

        {/* Center Canvas Area */}
        <div className="flex-1 h-full bg-white relative overflow-hidden">
          {activeSlideDetail ? (
            <ExcalidrawEditor
              key={activeSlideDetail.id}
              slide={activeSlideDetail}
              onRefreshSlide={() => selectSlide(activeSlideDetail.id)}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              Select or create a slide to edit
            </div>
          )}
        </div>

        {/* Right Versions / AI Panel */}
        <RightPanel />
      </div>

      {/* Export Progress Modal */}
      {isExporting && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 shadow-xl max-w-sm w-full text-center space-y-4">
            <div className="w-10 h-10 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center mx-auto">
              <Download className="w-5 h-5 animate-bounce" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800 mb-1">
                Exporting {exportType?.toUpperCase()}...
              </h3>
              <p className="text-xs text-slate-500">
                Rendering slide {exportProgress.current} of {exportProgress.total}
              </p>
            </div>

            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className="bg-brand-500 h-full transition-all duration-300"
                style={{
                  width: `${(exportProgress.current / Math.max(1, exportProgress.total)) * 100}%`,
                }}
              />
            </div>

            <button
              onClick={() => {
                cancelExportRef.current = true;
              }}
              className="px-4 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
