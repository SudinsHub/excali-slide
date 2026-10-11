import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import React, { useEffect } from 'react';
import { api } from '../../api/client';
import { SlideLight } from '../../types';

interface GenerationProgressProps {
  deckId: string;
  slides: SlideLight[];
  onSlideRetry: (slideId: string) => void;
  onAllReady: () => void;
  onCancel: () => void;
}

export const GenerationProgress: React.FC<GenerationProgressProps> = ({
  deckId,
  slides,
  onSlideRetry,
  onAllReady,
  onCancel,
}) => {
  const totalSlides = slides.length;
  const readySlides = slides.filter((s) => s.status === 'ready').length;
  const failedSlides = slides.filter((s) => s.status === 'failed').length;
  const inProgressSlides = slides.filter((s) => s.status === 'generating' || s.status === 'queued').length;

  const progressPercent = totalSlides > 0 ? Math.round((readySlides / totalSlides) * 100) : 0;

  // Auto-navigate when all slides are ready
  useEffect(() => {
    if (totalSlides > 0 && readySlides === totalSlides) {
      const timer = setTimeout(() => {
        onAllReady();
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [totalSlides, readySlides, onAllReady]);

  return (
    <div className="max-w-4xl mx-auto py-12 px-6 space-y-8">
      {/* Progress Header Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 tracking-tight">Generating Presentation Slides</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Compiling structured slide IR into editable Excalidraw scenes in parallel...
            </p>
          </div>

          <button
            onClick={onCancel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <XCircle className="w-3.5 h-3.5 text-slate-400" />
            <span>Cancel</span>
          </button>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold">
            <span className="text-slate-700">
              {readySlides} of {totalSlides} slides ready
            </span>
            <span className="text-brand-600">{progressPercent}%</span>
          </div>

          <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200/60">
            <div
              className="h-full bg-brand-600 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Slide Status Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        {slides.map((slide, idx) => {
          let statusBadge = null;
          let cardBorder = 'border-slate-200/90 bg-white';

          if (slide.status === 'ready') {
            cardBorder = 'border-emerald-200/90 bg-emerald-50/20';
            statusBadge = (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200/60">
                <CheckCircle2 className="w-3 h-3" />
                Ready
              </span>
            );
          } else if (slide.status === 'generating') {
            cardBorder = 'border-brand-300 bg-brand-50/20 shadow-xs';
            statusBadge = (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-brand-600 bg-brand-50 px-2 py-0.5 rounded-md border border-brand-200/60 animate-pulse">
                <Loader2 className="w-3 h-3 animate-spin" />
                Designing...
              </span>
            );
          } else if (slide.status === 'failed') {
            cardBorder = 'border-rose-200 bg-rose-50/20';
            statusBadge = (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-md border border-rose-200/60">
                <AlertCircle className="w-3 h-3" />
                Failed
              </span>
            );
          } else {
            statusBadge = (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-slate-500 bg-slate-50 px-2 py-0.5 rounded-md border border-slate-200/60">
                <Clock className="w-3 h-3" />
                Queued
              </span>
            );
          }

          return (
            <div
              key={slide.id}
              className={`rounded-2xl p-4 border transition-all shadow-xs flex flex-col justify-between h-36 ${cardBorder}`}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs font-bold text-slate-400">Slide {idx + 1}</span>
                {statusBadge}
              </div>

              <div className="my-auto">
                <div className="text-xs font-bold text-slate-800 line-clamp-2">
                  {slide.title || `Slide ${idx + 1}`}
                </div>
              </div>

              {/* Card Footer: Retry if failed */}
              <div className="flex items-center justify-between pt-1">
                <span className="text-[10px] text-slate-400 font-mono">
                  {slide.id.slice(0, 8)}
                </span>

                {slide.status === 'failed' && (
                  <button
                    onClick={() => onSlideRetry(slide.id)}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-semibold transition-colors shadow-xs"
                  >
                    <RefreshCw className="w-2.5 h-2.5" />
                    <span>Retry</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
