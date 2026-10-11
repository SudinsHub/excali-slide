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

  // Dev compiler
  async devCompile(ir: any, assetDims?: Record<string, [number, number]>): Promise<any> {
    const res = await fetch(`${API_BASE}/dev/compile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ir, asset_dims: assetDims || {} }),
    });
    return handleResponse<any>(res);
  },

  async devApplyIR(slideId: string, ir: any, assetDims?: Record<string, [number, number]>): Promise<any> {
    const res = await fetch(`${API_BASE}/dev/slides/${slideId}/apply-ir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ir, asset_dims: assetDims || {} }),
    });
    return handleResponse<any>(res);
  },

  // --- Pass 3 Endpoints ---

  // Resources
  async uploadResources(deckId: string, files: File[]): Promise<any[]> {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    const res = await fetch(`${API_BASE}/decks/${deckId}/resources`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<any[]>(res);
  },

  async getResources(deckId: string): Promise<any[]> {
    const res = await fetch(`${API_BASE}/decks/${deckId}/resources`);
    return handleResponse<any[]>(res);
  },

  async deleteResource(resourceId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/resources/${resourceId}`, {
      method: 'DELETE',
    });
    return handleResponse<void>(res);
  },

  // Plan
  async generatePlan(deckId: string): Promise<{ job_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/decks/${deckId}/plan/generate`, {
      method: 'POST',
    });
    return handleResponse<{ job_id: string; status: string }>(res);
  },

  async getPlan(deckId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/decks/${deckId}/plan`);
    return handleResponse<any>(res);
  },

  async updatePlan(deckId: string, plan: any): Promise<any> {
    const res = await fetch(`${API_BASE}/decks/${deckId}/plan`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(plan),
    });
    return handleResponse<any>(res);
  },

  async regeneratePlan(deckId: string, feedback?: string): Promise<{ job_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/decks/${deckId}/plan/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedback ? { feedback } : {}),
    });
    return handleResponse<{ job_id: string; status: string }>(res);
  },

  async approvePlan(deckId: string): Promise<{ status: string; slides_count: number }> {
    const res = await fetch(`${API_BASE}/decks/${deckId}/plan/approve`, {
      method: 'POST',
    });
    return handleResponse<{ status: string; slides_count: number }>(res);
  },

  // Slide regeneration
  async regenerateSlide(slideId: string): Promise<{ job_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/slides/${slideId}/regenerate`, {
      method: 'POST',
    });
    return handleResponse<{ job_id: string; status: string }>(res);
  },

  // Jobs
  async getJob(jobId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    return handleResponse<any>(res);
  },

  async cancelJob(jobId: string): Promise<{ id: string; status: string; cancel_requested: boolean }> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
      method: 'POST',
    });
    return handleResponse<{ id: string; status: string; cancel_requested: boolean }>(res);
  },
};
