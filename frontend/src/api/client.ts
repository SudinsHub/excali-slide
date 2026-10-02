import { Deck, DeckSettings, SlideDetail, SlideLight, VersionLight } from '../types';

const API_BASE = '/api';

export class ApiError extends Error {
  code: string;
  details: Record<string, any>;
  status: number;

  constructor(code: string, message: string, status: number, details: Record<string, any> = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errBody: any;
    try {
      errBody = await res.json();
    } catch {
      errBody = { error: { code: 'unknown_error', message: res.statusText, details: {} } };
    }
    const err = errBody?.error || {
      code: `http_${res.status}`,
      message: res.statusText,
      details: {},
    };
    throw new ApiError(err.code, err.message, res.status, err.details);
  }
  if (res.status === 204) {
    return null as T;
  }
  return res.json();
}

export const api = {
  // Decks
  async getDecks(): Promise<Deck[]> {
    const res = await fetch(`${API_BASE}/decks`);
    return handleResponse<Deck[]>(res);
  },

  async createDeck(title: string, settings?: Partial<DeckSettings>): Promise<Deck> {
    const res = await fetch(`${API_BASE}/decks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, settings: settings || {} }),
    });
    return handleResponse<Deck>(res);
  },

  async getDeck(deckId: string): Promise<Deck> {
    const res = await fetch(`${API_BASE}/decks/${deckId}`);
    return handleResponse<Deck>(res);
  },

  async updateDeck(deckId: string, data: { title?: string; settings?: Partial<DeckSettings> }): Promise<Deck> {
    const res = await fetch(`${API_BASE}/decks/${deckId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<Deck>(res);
  },

  async deleteDeck(deckId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/decks/${deckId}`, {
      method: 'DELETE',
    });
    return handleResponse<void>(res);
  },

  // Slides
  async getSlides(deckId: string): Promise<SlideLight[]> {
    const res = await fetch(`${API_BASE}/decks/${deckId}/slides`);
    return handleResponse<SlideLight[]>(res);
  },

  async createBlankSlide(deckId: string, position?: number): Promise<SlideDetail> {
    const res = await fetch(`${API_BASE}/decks/${deckId}/slides`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(position !== undefined ? { position } : {}),
    });
    return handleResponse<SlideDetail>(res);
  },

  async getSlide(slideId: string): Promise<SlideDetail> {
    const res = await fetch(`${API_BASE}/slides/${slideId}`);
    return handleResponse<SlideDetail>(res);
  },

  async reorderSlide(slideId: string, position: number): Promise<SlideDetail> {
    const res = await fetch(`${API_BASE}/slides/${slideId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position }),
    });
    return handleResponse<SlideDetail>(res);
  },

  async deleteSlide(slideId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/slides/${slideId}`, {
      method: 'DELETE',
    });
    return handleResponse<void>(res);
  },

  async duplicateSlide(slideId: string): Promise<SlideDetail> {
    const res = await fetch(`${API_BASE}/slides/${slideId}/duplicate`, {
      method: 'POST',
    });
    return handleResponse<SlideDetail>(res);
  },

  // Drafts
  async saveDraft(
    slideId: string,
    scene: any,
    ifRev: number,
    normalizingVersionId?: string | null
  ): Promise<SlideDetail> {
    const res = await fetch(`${API_BASE}/slides/${slideId}/draft`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scene,
        if_rev: ifRev,
        normalizing_version_id: normalizingVersionId || null,
      }),
    });
    return handleResponse<SlideDetail>(res);
  },

  // Versions
  async getVersions(slideId: string): Promise<VersionLight[]> {
    const res = await fetch(`${API_BASE}/slides/${slideId}/versions`);
    return handleResponse<VersionLight[]>(res);
  },

  async saveCheckpoint(slideId: string, summary?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/slides/${slideId}/versions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(summary ? { summary } : {}),
    });
    return handleResponse<any>(res);
  },

  async restoreVersion(slideId: string, versionId: string): Promise<SlideDetail> {
    const res = await fetch(`${API_BASE}/slides/${slideId}/restore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ version_id: versionId }),
    });
    return handleResponse<SlideDetail>(res);
  },

  // Assets
  async uploadAsset(deckId: string, fileId: string, blob: Blob): Promise<any> {
    const res = await fetch(`${API_BASE}/decks/${deckId}/assets/${fileId}`, {
      method: 'PUT',
      headers: { 'Content-Type': blob.type },
      body: blob,
    });
    return handleResponse<any>(res);
  },

  getAssetUrl(assetId: string): string {
    return `${API_BASE}/assets/${assetId}`;
  },

  async fetchAssetDataUrl(assetId: string): Promise<string> {
    const res = await fetch(`${API_BASE}/assets/${assetId}`);
    if (!res.ok) throw new Error(`Failed to load asset: ${assetId}`);
    const blob = await res.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  },

  // Dev sample deck
  async createSampleDeck(): Promise<Deck> {
    const res = await fetch(`${API_BASE}/dev/decks/sample`, {
      method: 'POST',
    });
    return handleResponse<Deck>(res);
  },
};
