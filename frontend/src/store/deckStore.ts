import { create } from 'zustand';
import { api } from '../api/client';
import { Deck, SaveStatus, SlideDetail, SlideLight } from '../types';

interface DeckState {
  currentDeck: Deck | null;
  slides: SlideLight[];
  activeSlideId: string | null;
  activeSlideDetail: SlideDetail | null;
  isLoading: boolean;
  saveStatus: SaveStatus;
  errorMessage: string | null;

  setCurrentDeck: (deck: Deck | null) => void;
  setSlides: (slides: SlideLight[]) => void;
  setActiveSlideId: (slideId: string | null) => void;
  setActiveSlideDetail: (detail: SlideDetail | null) => void;
  setSaveStatus: (status: SaveStatus, error?: string | null) => void;

  fetchDeckAndSlides: (deckId: string) => Promise<void>;
  selectSlide: (slideId: string) => Promise<void>;
  reorderSlides: (slideId: string, newPosition: number) => Promise<void>;
  createBlankSlide: (position?: number) => Promise<string>;
  duplicateSlide: (slideId: string) => Promise<string>;
  deleteSlide: (slideId: string) => Promise<void>;
}

export const useDeckStore = create<DeckState>((set, get) => ({
  currentDeck: null,
  slides: [],
  activeSlideId: null,
  activeSlideDetail: null,
  isLoading: false,
  saveStatus: 'saved',
  errorMessage: null,

  setCurrentDeck: (deck) => set({ currentDeck: deck }),
  setSlides: (slides) => set({ slides }),
  setActiveSlideId: (slideId) => set({ activeSlideId: slideId }),
  setActiveSlideDetail: (detail) => set({ activeSlideDetail: detail }),
  setSaveStatus: (status, error = null) => set({ saveStatus: status, errorMessage: error }),

  fetchDeckAndSlides: async (deckId: string) => {
    set({ isLoading: true, errorMessage: null });
    try {
      const [deck, slides] = await Promise.all([
        api.getDeck(deckId),
        api.getSlides(deckId),
      ]);
      set({ currentDeck: deck, slides, isLoading: false });
    } catch (err: any) {
      set({ isLoading: false, errorMessage: err.message || 'Failed to load deck' });
    }
  },

  selectSlide: async (slideId: string) => {
    set({ activeSlideId: slideId });
    try {
      const detail = await api.getSlide(slideId);
      set({ activeSlideDetail: detail });
    } catch (err: any) {
      set({ errorMessage: err.message || 'Failed to load slide' });
    }
  },

  reorderSlides: async (slideId: string, newPosition: number) => {
    const { slides, currentDeck } = get();
    if (!currentDeck) return;

    // Optimistic reorder
    const oldIndex = slides.findIndex((s) => s.id === slideId);
    if (oldIndex === -1 || oldIndex === newPosition) return;

    const newSlides = [...slides];
    const [moved] = newSlides.splice(oldIndex, 1);
    newSlides.splice(newPosition, 0, moved);
    const updatedPositions = newSlides.map((s, idx) => ({ ...s, position: idx }));
    set({ slides: updatedPositions });

    try {
      await api.reorderSlide(slideId, newPosition);
      // Refresh list to stay strictly in sync
      const freshSlides = await api.getSlides(currentDeck.id);
      set({ slides: freshSlides });
    } catch (err: any) {
      // Rollback on error
      set({ slides, errorMessage: err.message || 'Failed to reorder slides' });
    }
  },

  createBlankSlide: async (position?: number) => {
    const { currentDeck } = get();
    if (!currentDeck) throw new Error('No active deck');

    const newSlide = await api.createBlankSlide(currentDeck.id, position);
    const freshSlides = await api.getSlides(currentDeck.id);
    set({
      slides: freshSlides,
      activeSlideId: newSlide.id,
      activeSlideDetail: newSlide,
    });
    return newSlide.id;
  },

  duplicateSlide: async (slideId: string) => {
    const { currentDeck } = get();
    if (!currentDeck) throw new Error('No active deck');

    const dup = await api.duplicateSlide(slideId);
    const freshSlides = await api.getSlides(currentDeck.id);
    set({
      slides: freshSlides,
      activeSlideId: dup.id,
      activeSlideDetail: dup,
    });
    return dup.id;
  },

  deleteSlide: async (slideId: string) => {
    const { currentDeck, slides, activeSlideId } = get();
    if (!currentDeck) return;

    await api.deleteSlide(slideId);
    const freshSlides = await api.getSlides(currentDeck.id);

    let nextActiveId = activeSlideId;
    if (activeSlideId === slideId) {
      const deletedIdx = slides.findIndex((s) => s.id === slideId);
      const remaining = freshSlides.filter((s) => s.id !== slideId);
      if (remaining.length > 0) {
        const nextIdx = Math.min(deletedIdx, remaining.length - 1);
        nextActiveId = remaining[nextIdx].id;
      } else {
        nextActiveId = null;
      }
    }

    set({ slides: freshSlides, activeSlideId: nextActiveId });
    if (nextActiveId) {
      const detail = await api.getSlide(nextActiveId);
      set({ activeSlideDetail: detail });
    } else {
      set({ activeSlideDetail: null });
    }
  },
}));
