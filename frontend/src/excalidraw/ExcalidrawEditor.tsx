import {
  Excalidraw,
  getNonDeletedElements,
  getSceneVersion,
} from '@excalidraw/excalidraw';
import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { useDeckStore } from '../store/deckStore';
import { SlideDetail } from '../types';
import { loadSlideForEditor } from './normalize';

// Ensure asset path is configured for self-hosted font & binary assets
if (typeof window !== 'undefined') {
  (window as any).EXCALIDRAW_ASSET_PATH = '/';
}

interface Props {
  slide: SlideDetail;
  onRefreshSlide?: () => void;
}

export const ExcalidrawEditor: React.FC<Props> = ({ slide, onRefreshSlide }) => {
  const { setSaveStatus } = useDeckStore();
  const [excalidrawAPI, setExcalidrawAPI] = useState<any>(null);
  const [initialData, setInitialData] = useState<any>(null);
  const [isLoadingScene, setIsLoadingScene] = useState(true);

  // Tracking refs for debounced autosave
  const currentRevRef = useRef<number>(slide.draft?.rev ?? 0);
  const lastSavedVersionRef = useRef<number>(-1);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const currentSlideIdRef = useRef<string>(slide.id);

  // Keep refs in sync
  useEffect(() => {
    currentRevRef.current = slide.draft?.rev ?? 0;
    currentSlideIdRef.current = slide.id;
  }, [slide.id, slide.draft?.rev]);

  // Load and normalize scene data on slide change
  useEffect(() => {
    let isCancelled = false;
    setIsLoadingScene(true);

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
            setSaveStatus('saved');
          } catch (err) {
            console.warn('Failed initial normalization auto-save:', err);
          }
        }
      } catch (err: any) {
        console.error('Failed to load slide for editor:', err);
        setSaveStatus('error', err.message);
      } finally {
        if (!isCancelled) {
          setIsLoadingScene(false);
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

  // After Excalidraw mounts & loads content, zoom to fit the frame
  useEffect(() => {
    if (!excalidrawAPI || !initialData) return;

    // Small delay to ensure canvas elements are rendered
    const timer = setTimeout(() => {
      const elements = excalidrawAPI.getSceneElements();
      const frame = elements.find((el: any) => el.type === 'frame' || el.id === 'slide-frame');
      if (frame) {
        excalidrawAPI.scrollToContent(frame, {
          fitToViewport: true,
          viewportZoomFactor: 0.9,
          animate: false,
        });
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [excalidrawAPI, initialData]);

  // Scene change handler (debounced 800ms)
  const handleChange = (elements: readonly any[], appState: any, files: any) => {
    if (!excalidrawAPI || isLoadingScene) return;

    const nonDeleted = getNonDeletedElements(elements);
    const sceneVer = getSceneVersion(nonDeleted);

    // Only save when real elements changed (ignore pan / zoom / selection)
    if (sceneVer === lastSavedVersionRef.current) {
      return;
    }

    setSaveStatus('saving');

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(async () => {
      const slideIdToSave = currentSlideIdRef.current;
      const expectedRev = currentRevRef.current;

      try {
        // Upload any newly added pasted images to asset store
        if (files) {
          for (const fileId of Object.keys(files)) {
            const fileObj = files[fileId];
            if (fileObj?.dataURL && !fileObj.isUploaded) {
              try {
                const res = await fetch(fileObj.dataURL);
                const blob = await res.blob();
                await api.uploadAsset(slide.deck_id, fileId, blob);
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
        setSaveStatus('saved');
      } catch (err: any) {
        if (err.code === 'draft_conflict' || err.status === 409) {
          setSaveStatus('conflict', err.message);
        } else {
          setSaveStatus('error', err.message || 'Auto-save failed');
        }
      }
    }, 800);
  };

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
        key={slide.id}
        excalidrawAPI={(api) => setExcalidrawAPI(api)}
        initialData={initialData}
        onChange={handleChange}
        handleKeyboardGlobally={false}
        UIOptions={{
          canvasActions: {
            changeViewBackgroundColor: true,
            clearCanvas: false,
            loadScene: false,
            saveToActiveFile: false,
            export: false,
            saveAsImage: false,
          },
        }}
      />
    </div>
  );
};
