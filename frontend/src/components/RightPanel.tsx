import { Bookmark, Clock, History, RotateCcw, Sparkles } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useDeckStore } from '../store/deckStore';
import { VersionLight } from '../types';

export const RightPanel: React.FC = () => {
  const { activeSlideId, activeSlideDetail, selectSlide } = useDeckStore();
  const [activeTab, setActiveTab] = useState<'versions' | 'ai'>('versions');
  const [versions, setVersions] = useState<VersionLight[]>([]);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  const [isCheckpointing, setIsCheckpointing] = useState(false);

  const fetchVersions = async () => {
    if (!activeSlideId) return;
    setIsLoadingVersions(true);
    try {
      const data = await api.getVersions(activeSlideId);
      setVersions(data);
    } catch (err) {
      console.error('Failed to load versions', err);
    } finally {
      setIsLoadingVersions(false);
    }
  };

  useEffect(() => {
    fetchVersions();
  }, [activeSlideId, activeSlideDetail?.current_version?.seq]);

  const handleCheckpoint = async () => {
    if (!activeSlideId) return;
    const label = prompt('Enter a label for this checkpoint (optional):');
    if (label === null) return; // user cancelled

    setIsCheckpointing(true);
    try {
      await api.saveCheckpoint(activeSlideId, label || undefined);
      await selectSlide(activeSlideId);
      await fetchVersions();
    } catch (err: any) {
      alert(err.message || 'Failed to save checkpoint. Is the slide clean?');
    } finally {
      setIsCheckpointing(false);
    }
  };

  const handleRestore = async (version: VersionLight) => {
    if (!activeSlideId) return;
    const confirmed = confirm(
      `Restore to Version ${version.seq}? Any unsaved changes in your current draft will be committed to history automatically.`
    );
    if (!confirmed) return;

    try {
      await api.restoreVersion(activeSlideId, version.id);
      await selectSlide(activeSlideId);
      await fetchVersions();
    } catch (err: any) {
      alert(err.message || 'Failed to restore version');
    }
  };

  const formatOriginBadge = (origin: string) => {
    switch (origin) {
      case 'user_checkpoint':
        return { label: 'Checkpoint', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
      case 'restore':
        return { label: 'Restored', bg: 'bg-purple-50 text-purple-700 border-purple-200' };
      case 'user_save':
        return { label: 'Auto-save', bg: 'bg-slate-100 text-slate-700 border-slate-200' };
      case 'manual':
        return { label: 'Initial', bg: 'bg-blue-50 text-blue-700 border-blue-200' };
      case 'ai_generate':
      case 'ai_edit':
        return { label: 'AI', bg: 'bg-amber-50 text-amber-700 border-amber-200' };
      default:
        return { label: origin, bg: 'bg-slate-50 text-slate-600 border-slate-200' };
    }
  };

  return (
    <div className="w-80 border-l border-slate-200 bg-white flex flex-col h-full">
      {/* Tabs Header */}
      <div className="flex border-b border-slate-200 bg-slate-50/70 p-1 gap-1">
        <button
          onClick={() => setActiveTab('versions')}
          className={`flex-1 py-1.5 px-3 rounded text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors ${
            activeTab === 'versions'
              ? 'bg-white text-slate-900 shadow-sm border border-slate-200/80'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Versions</span>
        </button>
        <button
          onClick={() => setActiveTab('ai')}
          className={`flex-1 py-1.5 px-3 rounded text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors ${
            activeTab === 'ai'
              ? 'bg-white text-slate-900 shadow-sm border border-slate-200/80'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
          <span>AI Edit</span>
        </button>
      </div>

      {/* Tab 1: Versions */}
      {activeTab === 'versions' && (
        <div className="flex-1 flex flex-col min-h-0">
          <div className="p-3 border-b border-slate-100 flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600">History & Snapshots</span>
            <button
              onClick={handleCheckpoint}
              disabled={isCheckpointing}
              className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700 bg-brand-50 hover:bg-brand-100 px-2.5 py-1 rounded transition-colors disabled:opacity-50"
            >
              <Bookmark className="w-3.5 h-3.5" />
              <span>Checkpoint</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {isLoadingVersions && (
              <div className="text-xs text-slate-400 text-center py-4">Loading history...</div>
            )}
            {!isLoadingVersions && versions.length === 0 && (
              <div className="text-xs text-slate-400 text-center py-4">No versions recorded</div>
            )}
            {versions.map((v) => {
              const badge = formatOriginBadge(v.origin);
              const isCurrent = v.id === activeSlideDetail?.current_version?.id;
              const timeStr = new Date(v.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              });

              return (
                <div
                  key={v.id}
                  className={`p-2.5 rounded-lg border text-left transition-all ${
                    isCurrent
                      ? 'border-brand-500 bg-brand-50/30'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-slate-800">v{v.seq}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${badge.bg}`}>
                        {badge.label}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {timeStr}
                    </span>
                  </div>

                  {v.summary && (
                    <div className="text-xs text-slate-600 mb-2 font-medium line-clamp-2">
                      {v.summary}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-1">
                    {isCurrent ? (
                      <span className="text-[11px] font-semibold text-brand-600">Current active</span>
                    ) : (
                      <button
                        onClick={() => handleRestore(v)}
                        className="flex items-center gap-1 text-[11px] font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-2 py-0.5 rounded transition-colors"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>Restore</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: AI Placeholder */}
      {activeTab === 'ai' && (
        <div className="flex-1 flex flex-col p-4">
          <div className="rounded-xl border border-dashed border-amber-300 bg-amber-50/50 p-4 text-center mb-4">
            <Sparkles className="w-8 h-8 text-amber-500 mx-auto mb-2" />
            <h4 className="text-sm font-semibold text-amber-900 mb-1">AI Assistant</h4>
            <p className="text-xs text-amber-700 leading-relaxed">
              Automated slide generation, diagram synthesis, and structured editing will arrive in Pass 3 & 4.
            </p>
          </div>

          <div className="space-y-3 mt-auto">
            <textarea
              disabled
              placeholder="Prompt AI to edit this slide (Available in Pass 4)..."
              className="w-full h-24 text-xs p-2.5 rounded-lg border border-slate-200 bg-slate-100 text-slate-400 resize-none cursor-not-allowed"
            />
            <button
              disabled
              className="w-full py-2 bg-slate-200 text-slate-400 rounded-lg text-xs font-semibold cursor-not-allowed"
            >
              Generate AI Edit
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
