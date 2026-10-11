import {
  ArrowLeft,
  Download,
  FileArchive,
  FileText,
  Loader2,
  Play,
  Sparkles,
} from 'lucide-react';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { useDeckEvents } from '../api/useDeckEvents';
import { BriefStep } from '../components/pipeline/BriefStep';
import { GenerationProgress } from '../components/pipeline/GenerationProgress';
import { PlanStep } from '../components/pipeline/PlanStep';
import { RightPanel } from '../components/RightPanel';
import { SaveStateIndicator } from '../components/SaveStateIndicator';
import { ThumbnailsRail } from '../components/ThumbnailsRail';
import { ExcalidrawEditor } from '../excalidraw/ExcalidrawEditor';
import { exportDeckToPdf } from '../export/exportPdf';
import { exportDeckToZip, slugify } from '../export/exportZip';
import { useDeckStore } from '../store/deckStore';
import { Resource, SlideDetail } from '../types';

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
  const [resources, setResources] = useState<Resource[]>([]);
  const [activeJobsCount, setActiveJobsCount] = useState(0);

  // Workflow step: brief | plan | generating | slides
  const [activeStep, setActiveStep] = useState<'brief' | 'plan' | 'generating' | 'slides'>('slides');

  // Export progress modal state
  const [isExporting, setIsExporting] = useState(false);
  const [exportType, setExportType] = useState<'pdf' | 'zip' | null>(null);
  const [exportProgress, setExportProgress] = useState<{ current: number; total: number }>({
    current: 0,
    total: 0,
  });
  const cancelExportRef = useRef(false);

  // Load resources
  const loadResources = useCallback(async () => {
    if (!deckId) return;
    try {
      const res = await api.getResources(deckId);
      setResources(res);
    } catch (err) {
      console.warn('Failed to load resources:', err);
    }
  }, [deckId]);

  // Initial load
  useEffect(() => {
    if (deckId) {
      fetchDeckAndSlides(deckId);
      loadResources();
    }
  }, [deckId, loadResources]);

  // Determine initial step based on deck status
  useEffect(() => {
    if (!currentDeck) return;
    setDeckTitle(currentDeck.title);

    const stepQuery = searchParams.get('step');
    if (stepQuery && ['brief', 'plan', 'slides'].includes(stepQuery)) {
      setActiveStep(stepQuery as any);
      return;
    }

    if (currentDeck.status === 'draft' || currentDeck.status === 'ingesting') {
      setActiveStep('brief');
    } else if (currentDeck.status === 'planning' || currentDeck.status === 'plan_review') {
      setActiveStep('plan');
    } else if (currentDeck.status === 'generating') {
      setActiveStep('generating');
    } else {
      setActiveStep('slides');
    }
  }, [currentDeck?.id, currentDeck?.status]);

  // Live SSE updates
  useDeckEvents(deckId, {
    onSnapshot: (data) => {
      if (data.deck) setCurrentDeck({ ...currentDeck, ...data.deck });
      if (data.resources) setResources(data.resources);
      if (data.jobs) setActiveJobsCount(data.jobs.length);
      if (data.slides && data.slides.length > 0) {
        if (deckId) fetchDeckAndSlides(deckId);
      }
    },
    onDeckChange: (d) => {
      if (currentDeck) {
        setCurrentDeck({ ...currentDeck, status: d.status, current_plan_id: d.current_plan_id });
      }
      if (d.status === 'ready' && activeStep === 'generating') {
        setActiveStep('slides');
        if (deckId) fetchDeckAndSlides(deckId);
      } else if (d.status === 'plan_review' && activeStep === 'brief') {
        setActiveStep('plan');
      } else if (d.status === 'generating' && activeStep !== 'generating') {
        setActiveStep('generating');
        if (deckId) fetchDeckAndSlides(deckId);
      }
    },
    onSlideChange: () => {
      if (deckId) fetchDeckAndSlides(deckId);
    },
    onResourceChange: () => {
      loadResources();
    },
    onJobChange: (j) => {
      if (j.status === 'queued' || j.status === 'running') {
        setActiveJobsCount((prev) => Math.max(1, prev));
      } else {
        setActiveJobsCount((prev) => Math.max(0, prev - 1));
      }
    },
  });

  // Handle slide selection based on URL search query or default to first slide
  useEffect(() => {
    if (slides.length === 0 || activeStep !== 'slides') return;

    const querySlideId = searchParams.get('slide');
    if (querySlideId && slides.some((s) => s.id === querySlideId)) {
      if (activeSlideId !== querySlideId) {
        selectSlide(querySlideId);
      }
    } else {
      const firstSlide = slides[0];
      selectSlide(firstSlide.id);
      setSearchParams({ slide: firstSlide.id, step: 'slides' }, { replace: true });
    }
  }, [slides, activeStep]);

  // Keyboard navigation Alt+Up / Alt+Down between slides
  useEffect(() => {
    if (activeStep !== 'slides') return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      if (e.altKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
        e.preventDefault();
        const currentIdx = slides.findIndex((s) => s.id === activeSlideId);
        if (currentIdx === -1) return;

        if (e.key === 'ArrowUp' && currentIdx > 0) {
          selectSlide(slides[currentIdx - 1].id);
        } else if (e.key === 'ArrowDown' && currentIdx < slides.length - 1) {
          selectSlide(slides[currentIdx + 1].id);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [slides, activeSlideId, selectSlide, activeStep]);

  const handleTitleSubmit = async () => {
    if (!currentDeck || !deckTitle.trim()) {
      setIsEditingTitle(false);
      return;
    }
    if (deckTitle.trim() === currentDeck.title) {
      setIsEditingTitle(false);
      return;
    }

    try {
      const updated = await api.updateDeck(currentDeck.id, { title: deckTitle.trim() });
      setCurrentDeck(updated);
    } catch (err: any) {
      alert(err.message || 'Failed to rename deck');
    } finally {
      setIsEditingTitle(false);
    }
  };

  const handlePresent = () => {
    if (!currentDeck) return;
    navigate(`/present/${currentDeck.id}`);
  };

  const handleExportPdf = async (quality: 'standard' | 'high' = 'high') => {
    if (!currentDeck || slides.length === 0) return;
    setIsExporting(true);
    setExportType('pdf');
    setExportProgress({ current: 0, total: slides.length });
    cancelExportRef.current = false;

    try {
      const fullSlides = await Promise.all(slides.map((s) => api.getSlide(s.id)));
      const pdfBlob = await exportDeckToPdf(fullSlides, currentDeck.title, {
        quality,
        onProgress: (current: number, total: number) => {
          setExportProgress({ current, total });
        },
        isCancelled: () => cancelExportRef.current,
      });

      const url = URL.createObjectURL(pdfBlob);
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
      const fullSlides = await Promise.all(slides.map((s) => api.getSlide(s.id)));
      const zipBlob = await exportDeckToZip(fullSlides, currentDeck.title, {
        onProgress: (current: number, total: number) => {
          setExportProgress({ current, total });
        },
        isCancelled: () => cancelExportRef.current,
      });

      const url = URL.createObjectURL(zipBlob);
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

  const handleRefreshSlide = useCallback(() => {
    if (activeSlideId) {
      selectSlide(activeSlideId);
    }
  }, [activeSlideId, selectSlide]);

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
      <header className="h-14 border-b border-slate-200 bg-white px-4 flex items-center justify-between z-10 shrink-0">
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
            <button
              onClick={() => {
                setActiveStep('brief');
                setSearchParams({ step: 'brief' }, { replace: true });
              }}
              className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                activeStep === 'brief'
                  ? 'bg-brand-50 text-brand-700 font-semibold border border-brand-200'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
              }`}
            >
              1. Brief
            </button>
            <span className="text-slate-300">›</span>
            <button
              onClick={() => {
                setActiveStep('plan');
                setSearchParams({ step: 'plan' }, { replace: true });
              }}
              className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                activeStep === 'plan' || activeStep === 'generating'
                  ? 'bg-brand-50 text-brand-700 font-semibold border border-brand-200'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
              }`}
            >
              2. Plan
            </button>
            <span className="text-slate-300">›</span>
            <button
              onClick={() => {
                setActiveStep('slides');
                setSearchParams({ step: 'slides' }, { replace: true });
              }}
              className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                activeStep === 'slides'
                  ? 'bg-brand-50 text-brand-700 font-semibold border border-brand-200'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
              }`}
            >
              3. Slides
            </button>
          </div>
        </div>

        {/* Right Action Tools */}
        <div className="flex items-center gap-2.5">
          {/* Active Job indicator */}
          {activeJobsCount > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-xs font-semibold animate-pulse">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Jobs active</span>
            </div>
          )}

          {activeStep === 'slides' && (
            <>
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
            </>
          )}
        </div>
      </header>

      {/* Main Workspace Body by Step */}
      <div className="flex-1 overflow-auto">
        {activeStep === 'brief' && (
          <BriefStep
            deck={currentDeck}
            resources={resources}
            onDeckUpdated={setCurrentDeck}
            onResourcesChanged={loadResources}
            onProceedToPlan={() => {
              setActiveStep('plan');
              setSearchParams({ step: 'plan' }, { replace: true });
            }}
          />
        )}

        {activeStep === 'plan' && (
          <PlanStep
            deckId={currentDeck.id}
            resources={resources}
            deck={currentDeck}
            onBackToBrief={() => {
              setActiveStep('brief');
              setSearchParams({ step: 'brief' }, { replace: true });
            }}
            onPlanApproved={() => {
              setActiveStep('generating');
              if (deckId) fetchDeckAndSlides(deckId);
            }}
          />
        )}

        {activeStep === 'generating' && (
          <GenerationProgress
            deckId={currentDeck.id}
            slides={slides}
            onSlideRetry={(slideId) => {
              api.regenerateSlide(slideId).then(() => {
                if (deckId) fetchDeckAndSlides(deckId);
              }).catch(console.error);
            }}
            onAllReady={() => {
              setActiveStep('slides');
              setSearchParams({ step: 'slides' }, { replace: true });
              if (deckId) fetchDeckAndSlides(deckId);
            }}
            onCancel={() => {
              setActiveStep('plan');
              setSearchParams({ step: 'plan' }, { replace: true });
            }}
          />
        )}

        {activeStep === 'slides' && (
          <div className="h-full flex overflow-hidden">
            {/* Left Thumbnails Rail */}
            <ThumbnailsRail />

            {/* Center Canvas Area */}
            <div className="flex-1 h-full bg-white relative overflow-hidden">
              {activeSlideDetail ? (
                <ExcalidrawEditor
                  key={activeSlideDetail.id}
                  slide={activeSlideDetail}
                  onRefreshSlide={handleRefreshSlide}
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
        )}
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
