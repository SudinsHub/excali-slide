import { Copy, GripVertical, Plus, Trash2 } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { renderSlidePng } from '../export/renderSlidePng';
import { useDeckStore } from '../store/deckStore';

// In-memory cache for slide thumbnail blob URLs: `${slideId}:${rev}` -> url
const thumbnailCache = new Map<string, string>();

export const ThumbnailsRail: React.FC = () => {
  const {
    slides,
    activeSlideId,
    selectSlide,
    reorderSlides,
    createBlankSlide,
    duplicateSlide,
    deleteSlide,
  } = useDeckStore();

  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);
  const [thumbnails, setThumbnails] = useState<Record<string, string>>({});

  // Generate thumbnail previews when slides change
  useEffect(() => {
    let isSubscribed = true;

    async function loadThumbnails() {
      for (const slide of slides) {
        const cacheKey = `${slide.id}:${slide.draft_rev}`;
        if (thumbnailCache.has(cacheKey)) {
          if (isSubscribed) {
            setThumbnails((prev) => ({ ...prev, [slide.id]: thumbnailCache.get(cacheKey)! }));
          }
          continue;
        }

        try {
          const detail = await api.getSlide(slide.id);
          const blob = await renderSlidePng(detail, 0.15, api.fetchAssetDataUrl);
          const url = URL.createObjectURL(blob);
          thumbnailCache.set(cacheKey, url);
          if (isSubscribed) {
            setThumbnails((prev) => ({ ...prev, [slide.id]: url }));
          }
        } catch {
          // Fallback or ignore preview failure
        }
      }
    }

    loadThumbnails();

    return () => {
      isSubscribed = false;
    };
  }, [slides]);

  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIdx(index);
    e.dataTransfer.setData('text/plain', String(index));
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverIdx !== index) {
      setDragOverIdx(index);
    }
  };

  const handleDrop = async (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    if (draggedIdx === null || draggedIdx === targetIndex) {
      setDraggedIdx(null);
      setDragOverIdx(null);
      return;
    }
    const slideToMove = slides[draggedIdx];
    setDraggedIdx(null);
    setDragOverIdx(null);
    await reorderSlides(slideToMove.id, targetIndex);
  };

  return (
    <div className="w-64 border-r border-slate-200 bg-white flex flex-col h-full select-none">
      <div className="p-3 border-b border-slate-100 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Slides ({slides.length})
        </span>
        <button
          onClick={() => createBlankSlide()}
          className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700 bg-brand-50 hover:bg-brand-100 px-2.5 py-1 rounded transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {slides.map((slide, idx) => {
          const isActive = slide.id === activeSlideId;
          const isOver = dragOverIdx === idx;
          const thumbUrl = thumbnails[slide.id];

          return (
            <div
              key={slide.id}
              draggable
              onDragStart={(e) => handleDragStart(e, idx)}
              onDragOver={(e) => handleDragOver(e, idx)}
              onDrop={(e) => handleDrop(e, idx)}
              onClick={() => selectSlide(slide.id)}
              className={`group relative rounded-lg border text-left transition-all cursor-pointer ${
                isActive
                  ? 'border-brand-500 ring-2 ring-brand-100 shadow-sm'
                  : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
              } ${isOver ? 'border-t-4 border-t-brand-500' : ''}`}
            >
              {/* Slide Number & Title Header */}
              <div className="flex items-center justify-between px-2.5 py-1.5 bg-slate-50 border-b border-slate-100 rounded-t-lg">
                <div className="flex items-center gap-1.5 min-w-0">
                  <GripVertical className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-600 cursor-grab" />
                  <span className="text-xs font-semibold text-slate-600">
                    {idx + 1}
                  </span>
                  <span className="text-xs text-slate-700 font-medium truncate max-w-[120px]">
                    {slide.title || 'Untitled'}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      duplicateSlide(slide.id);
                    }}
                    title="Duplicate slide"
                    className="p-1 hover:bg-slate-200 rounded text-slate-600"
                  >
                    <Copy className="w-3 h-3" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (slides.length <= 1) {
                        alert('Cannot delete the last slide');
                        return;
                      }
                      if (confirm('Delete this slide?')) {
                        deleteSlide(slide.id);
                      }
                    }}
                    title="Delete slide"
                    className="p-1 hover:bg-red-100 rounded text-red-600"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>

              {/* Thumbnail Container (16:9 ratio) */}
              <div className="relative aspect-video bg-white rounded-b-lg overflow-hidden flex items-center justify-center">
                {thumbUrl ? (
                  <img
                    src={thumbUrl}
                    alt={`Slide ${idx + 1}`}
                    className="w-full h-full object-contain pointer-events-none"
                  />
                ) : (
                  <div className="text-[10px] text-slate-400 flex flex-col items-center">
                    <span>1920×1080</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
