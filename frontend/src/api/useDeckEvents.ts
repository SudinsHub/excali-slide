import { useEffect, useRef } from 'react';

export interface DeckEventsCallbacks {
  onSnapshot?: (data: { deck: any; slides: any[]; jobs: any[]; resources: any[] }) => void;
  onDeckChange?: (data: { id: string; status: string; current_plan_id: string | null }) => void;
  onSlideChange?: (data: { id: string; position: number; plan_key: string | null; status: string; error: string | null; current_version_id: string | null; deleted: boolean }) => void;
  onJobChange?: (data: { id: string; slide_id: string | null; kind: string; status: string; progress: any; error: string | null }) => void;
  onResourceChange?: (data: { id: string; kind: string; filename: string; status: string; error: string | null }) => void;
}

export function useDeckEvents(deckId: string | undefined, callbacks: DeckEventsCallbacks) {
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  useEffect(() => {
    if (!deckId) return;

    let eventSource: EventSource | null = null;
    let reconnectTimeout: any = null;

    function connect() {
      eventSource = new EventSource(`/api/decks/${deckId}/events`);

      eventSource.addEventListener('snapshot', (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          callbacksRef.current.onSnapshot?.(data);
        } catch (err) {
          console.warn('Failed to parse SSE snapshot:', err);
        }
      });

      eventSource.addEventListener('deck', (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          callbacksRef.current.onDeckChange?.(data);
        } catch (err) {
          console.warn('Failed to parse SSE deck event:', err);
        }
      });

      eventSource.addEventListener('slide', (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          callbacksRef.current.onSlideChange?.(data);
        } catch (err) {
          console.warn('Failed to parse SSE slide event:', err);
        }
      });

      eventSource.addEventListener('job', (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          callbacksRef.current.onJobChange?.(data);
        } catch (err) {
          console.warn('Failed to parse SSE job event:', err);
        }
      });

      eventSource.addEventListener('resource', (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          callbacksRef.current.onResourceChange?.(data);
        } catch (err) {
          console.warn('Failed to parse SSE resource event:', err);
        }
      });

      eventSource.onerror = () => {
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        // Auto-reconnect after 3s
        reconnectTimeout = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [deckId]);
}
