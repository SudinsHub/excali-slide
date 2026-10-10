import {
  Excalidraw,
  getNonDeletedElements,
  getSceneVersion,
} from '@excalidraw/excalidraw';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { useDeckStore } from '../store/deckStore';
import { SlideDetail } from '../types';
import { loadSlideForEditor } from './normalize';

// Ensure asset path is configured for self-hosted font & binary assets
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
};

interface Props {
  slide: SlideDetail;
  onRefreshSlide?: () => void;
}

export const ExcalidrawEditor: React.FC<Props> = React.memo(({ slide }) => {
  const excalidrawAPIRef = useRef<any>(null);
  const [initialData, setInitialData] = useState<any>(null);
  const [isLoadingScene, setIsLoadingScene] = useState(true);
  const isLoadingSceneRef = useRef(true);

  // Tracking refs for debounced autosave
  const currentRevRef = useRef<number>(slide.draft?.rev ?? 0);
  const lastSavedVersionRef = useRef<number>(-1);
  const lastSeenVersionRef = useRef<number>(-1);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const currentSlideIdRef = useRef<string>(slide.id);
  const currentDeckIdRef = useRef<string>(slide.deck_id);
  const hasFittedRef = useRef(false);

  // Keep refs in sync
  useEffect(() => {
    currentRevRef.current = slide.draft?.rev ?? 0;
    currentSlideIdRef.current = slide.id;
    currentDeckIdRef.current = slide.deck_id;
  }, [slide.id, slide.draft?.rev, slide.deck_id]);

  // Load and normalize scene data on slide change
  useEffect(() => {
    let isCancelled = false;
    setIsLoadingScene(true);
    isLoadingSceneRef.current = true;
    hasFittedRef.current = false;

    async function prepareScene() {
      try {
        const { scene, didNormalize, normalizingVersionId } = await loadSlideForEditor(
          slide,
          api.fetchAssetDataUrl
        );

        if (isCancelled) return;

        setInitialData({
          elements: scene.elements,
          appState: {
            ...scene.appState,
            viewBackgroundColor: '#ffffff',
            isLoading: false,
          },
          files: scene.files,
        });

        const initialSceneVersion = getSceneVersion(scene.elements);
        lastSavedVersionRef.current = initialSceneVersion;
        lastSeenVersionRef.current = initialSceneVersion;

        // If normalization happened on the client, save it once to backend draft
        if (didNormalize && normalizingVersionId) {
          try {
            const updated = await api.saveDraft(
              slide.id,
              { elements: scene.elements, appState: { viewBackgroundColor: '#ffffff' } },
              currentRevRef.current,
              normalizingVersionId
            );
            currentRevRef.current = updated.draft?.rev ?? currentRevRef.current + 1;
            useDeckStore.getState().setSaveStatus('saved');
          } catch (err) {
            console.warn('Failed initial normalization auto-save:', err);
          }
        }
      } catch (err: any) {
        console.error('Failed to load slide for editor:', err);
        useDeckStore.getState().setSaveStatus('error', err.message);
      } finally {
        if (!isCancelled) {
          setIsLoadingScene(false);
          isLoadingSceneRef.current = false;
        }
      }
    }

    prepareScene();

    return () => {
      isCancelled = true;
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [slide.id]);

  const handleExcalidrawAPI = useCallback((api: any) => {
    excalidrawAPIRef.current = api;
  }, []);

  // Zoom to fit the frame once after elements load
  useEffect(() => {
    if (!initialData || hasFittedRef.current) return;

    const timer = setTimeout(() => {
      const api = excalidrawAPIRef.current;
      if (!api) return;
      const elements = api.getSceneElements();
      const frame = elements.find((el: any) => el.type === 'frame' || el.id === 'slide-frame');
      if (frame) {
        api.scrollToContent(frame, {
          fitToViewport: true,
          viewportZoomFactor: 0.9,
          animate: false,
        });
        hasFittedRef.current = true;
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [initialData]);

  // Scene change handler (debounced 800ms)
  const handleChange = useCallback((elements: readonly any[], appState: any, files: any) => {
    if (!excalidrawAPIRef.current || isLoadingSceneRef.current) return;

    const nonDeleted = getNonDeletedElements(elements);
    const sceneVer = getSceneVersion(nonDeleted);

    // If scene elements have not changed since last registered change, do nothing
    // (prevents infinite loop triggered by Excalidraw's internal componentDidUpdate)
    if (sceneVer === lastSeenVersionRef.current) {
      return;
    }

    lastSeenVersionRef.current = sceneVer;

    // Only set saving status if not already saving
    if (useDeckStore.getState().saveStatus !== 'saving') {
      useDeckStore.getState().setSaveStatus('saving');
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(async () => {
      const slideIdToSave = currentSlideIdRef.current;
      const expectedRev = currentRevRef.current;
      const deckId = currentDeckIdRef.current;

      try {
        // Upload any newly added pasted images to asset store
        if (files) {
          for (const fileId of Object.keys(files)) {
            const fileObj = files[fileId];
            if (fileObj?.dataURL && !fileObj.isUploaded) {
              try {
                const res = await fetch(fileObj.dataURL);
                const blob = await res.blob();
                await api.uploadAsset(deckId, fileId, blob);
                fileObj.isUploaded = true;
              } catch (assetErr) {
                console.warn('Failed to upload pasted asset:', assetErr);
              }
            }
          }
        }

        const scenePayload = {
          elements: nonDeleted,
          appState: { viewBackgroundColor: appState.viewBackgroundColor || '#ffffff' },
        };

        const updatedSlide = await api.saveDraft(
          slideIdToSave,
          scenePayload,
          expectedRev
        );

        lastSavedVersionRef.current = sceneVer;
        currentRevRef.current = updatedSlide.draft?.rev ?? expectedRev + 1;
        useDeckStore.getState().setSaveStatus('saved');
      } catch (err: any) {
        if (err.code === 'draft_conflict' || err.status === 409) {
          useDeckStore.getState().setSaveStatus('conflict', err.message);
        } else {
          useDeckStore.getState().setSaveStatus('error', err.message || 'Auto-save failed');
        }
      }
    }, 800);
  }, []);

  if (isLoadingScene || !initialData) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-slate-50">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-3 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-medium text-slate-500">Preparing Excalidraw canvas...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative" style={{ height: '100%' }}>
      <Excalidraw
        excalidrawAPI={handleExcalidrawAPI}
        initialData={initialData}
        onChange={handleChange}
        handleKeyboardGlobally={false}
        UIOptions={UI_OPTIONS}
      />
    </div>
  );
});
