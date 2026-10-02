import { ArrowLeft, Maximize, Minimize } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { renderSlidePng } from '../export/renderSlidePng';
import { SlideDetail } from '../types';

export const PresentPage: React.FC = () => {
  const { id: deckId } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [slides, setSlides] = useState<SlideDetail[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [slideImages, setSlideImages] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [showCounter, setShowCounter] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const counterTimerRef = useRef<NodeJS.Timeout | null>(null);
  const touchStartXRef = useRef<number | null>(null);

  // 1. Load all slide details for this deck
  useEffect(() => {
    let isCancelled = false;

    async function loadDeckSlides() {
      if (!deckId) return;
      setIsLoading(true);
      try {
        const lightList = await api.getSlides(deckId);
        const fullList: SlideDetail[] = [];
        for (const s of lightList) {
          const detail = await api.getSlide(s.id);
          fullList.push(detail);
        }

        if (isCancelled) return;
        setSlides(fullList);

        // Initial slide from search query
        const querySlideId = searchParams.get('slide');
        if (querySlideId) {
          const foundIdx = fullList.findIndex((s) => s.id === querySlideId);
          if (foundIdx !== -1) {
            setCurrentIndex(foundIdx);
          }
        }
      } catch (err) {
        console.error('Failed to load presentation slides:', err);
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    loadDeckSlides();
    return () => {
      isCancelled = true;
    };
  }, [deckId]);

  // 2. Render and cache PNG images with prefetching of next and previous
  useEffect(() => {
    if (slides.length === 0) return;

    const scale = Math.min(2, window.devicePixelRatio || 1);
    const indicesToLoad = [currentIndex];
    if (currentIndex + 1 < slides.length) indicesToLoad.push(currentIndex + 1);
    if (currentIndex - 1 >= 0) indicesToLoad.push(currentIndex - 1);

    indicesToLoad.forEach(async (idx) => {
      const slide = slides[idx];
      if (slideImages[slide.id]) return;

      try {
        const blob = await renderSlidePng(slide, scale, api.fetchAssetDataUrl);
        const url = URL.createObjectURL(blob);
        setSlideImages((prev) => ({ ...prev, [slide.id]: url }));
      } catch (err) {
        console.warn(`Failed to render slide image for index ${idx}:`, err);
      }
    });
  }, [currentIndex, slides]);

  // Counter fade timer
  const triggerCounterVisibility = () => {
    setShowCounter(true);
    if (counterTimerRef.current) {
      clearTimeout(counterTimerRef.current);
    }
    counterTimerRef.current = setTimeout(() => {
      setShowCounter(false);
    }, 2000);
  };

  const goToSlide = (newIndex: number) => {
    if (newIndex >= 0 && newIndex < slides.length) {
      setCurrentIndex(newIndex);
      triggerCounterVisibility();
    }
  };

  const handleNext = () => goToSlide(currentIndex + 1);
  const handlePrev = () => goToSlide(currentIndex - 1);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  const handleExit = () => {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    const currentSlide = slides[currentIndex];
    navigate(`/decks/${deckId}?slide=${currentSlide ? currentSlide.id : ''}`);
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      triggerCounterVisibility();

      switch (e.key) {
        case 'ArrowRight':
        case ' ':
        case 'PageDown':
          e.preventDefault();
          handleNext();
          break;
        case 'ArrowLeft':
        case 'PageUp':
          e.preventDefault();
          handlePrev();
          break;
        case 'Home':
          e.preventDefault();
          goToSlide(0);
          break;
        case 'End':
          e.preventDefault();
          goToSlide(slides.length - 1);
          break;
        case 'f':
        case 'F':
          e.preventDefault();
          toggleFullscreen();
          break;
        case 'Escape':
          e.preventDefault();
          handleExit();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentIndex, slides]);

  // Mouse click zones
  const handleScreenClick = (e: React.MouseEvent) => {
    const width = window.innerWidth;
    const x = e.clientX;
    triggerCounterVisibility();

    if (x < width / 3) {
      handlePrev();
    } else if (x > (width * 2) / 3) {
      handleNext();
    }
  };

  // Touch swipe support
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartXRef.current = e.touches[0].clientX;
    triggerCounterVisibility();
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartXRef.current === null) return;
    const endX = e.changedTouches[0].clientX;
    const diff = endX - touchStartXRef.current;
    touchStartXRef.current = null;

    if (Math.abs(diff) > 50) {
      if (diff > 0) {
        handlePrev(); // swipe right -> previous
      } else {
        handleNext(); // swipe left -> next
      }
    }
  };

  if (isLoading || slides.length === 0) {
    return (
      <div className="fixed inset-0 bg-black flex items-center justify-center text-white text-sm">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          <span>Preparing presentation slides...</span>
        </div>
      </div>
    );
  }

  const currentSlide = slides[currentIndex];
  const currentImageUrl = slideImages[currentSlide.id];

  return (
    <div
      onClick={handleScreenClick}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      className="fixed inset-0 bg-black flex items-center justify-center select-none overflow-hidden cursor-pointer"
    >
      {/* Top Floating Bar */}
      <div
        className={`fixed top-4 left-4 right-4 flex items-center justify-between text-white/70 transition-opacity duration-300 z-50 pointer-events-none ${
          showCounter ? 'opacity-100' : 'opacity-0'
        }`}
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleExit();
          }}
          className="pointer-events-auto flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 backdrop-blur-md text-xs font-semibold text-white transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Exit Presentation</span>
        </button>

        <button
          onClick={(e) => {
            e.stopPropagation();
            toggleFullscreen();
          }}
          className="pointer-events-auto p-2 rounded-full bg-white/10 hover:bg-white/20 backdrop-blur-md text-white transition-colors"
          title="Toggle Fullscreen (F)"
        >
          {isFullscreen ? <Minimize className="w-4 h-4" /> : <Maximize className="w-4 h-4" />}
        </button>
      </div>

      {/* Slide Image Scaled to 16:9 Letterboxed */}
      <div className="w-full h-full flex items-center justify-center p-2">
        {currentImageUrl ? (
          <img
            src={currentImageUrl}
            alt={`Slide ${currentIndex + 1}`}
            className="max-w-full max-h-full aspect-video object-contain shadow-2xl rounded-sm"
          />
        ) : (
          <div className="text-white/40 text-xs flex flex-col items-center gap-2">
            <div className="w-6 h-6 border border-white/20 border-t-white rounded-full animate-spin" />
            <span>Rendering slide {currentIndex + 1}...</span>
          </div>
        )}
      </div>

      {/* Floating Slide Counter in Bottom-Right */}
      <div
        className={`fixed bottom-4 right-4 bg-black/60 backdrop-blur-md text-white/90 text-xs px-3 py-1.5 rounded-full font-mono transition-opacity duration-300 pointer-events-none ${
          showCounter ? 'opacity-100' : 'opacity-0'
        }`}
      >
        {currentIndex + 1} / {slides.length}
      </div>
    </div>
  );
};
