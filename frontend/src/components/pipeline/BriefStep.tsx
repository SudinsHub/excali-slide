import {
  AlertCircle,
  CheckCircle2,
  FileCode,
  FileSpreadsheet,
  FileText,
  ImageIcon,
  Loader2,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react';
import React, { useCallback, useRef, useState } from 'react';
import { api } from '../../api/client';
import { Deck, DeckSettings, Resource } from '../../types';

interface BriefStepProps {
  deck: Deck;
  resources: Resource[];
  onDeckUpdated: (deck: Deck) => void;
  onResourcesChanged: () => void;
  onProceedToPlan: () => void;
}

export const BriefStep: React.FC<BriefStepProps> = ({
  deck,
  resources,
  onDeckUpdated,
  onResourcesChanged,
  onProceedToPlan,
}) => {
  const [briefTitle, setBriefTitle] = useState(deck.title || '');
  const [settings, setSettings] = useState<DeckSettings>(() => ({
    slide_count: deck.settings?.slide_count ?? null,
    tone: deck.settings?.tone ?? 'professional',
    diagram_intensity: deck.settings?.diagram_intensity ?? 'medium',
    density: deck.settings?.density ?? 'standard',
    audience: deck.settings?.audience ?? 'general audience',
    language: deck.settings?.language ?? 'English',
    extra_instructions: deck.settings?.extra_instructions ?? '',
  }));

  const [isAutoSlideCount, setIsAutoSlideCount] = useState<boolean>(deck.settings?.slide_count == null);
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check if any file is still parsing
  const isAnyFileParsing = isUploading || resources.some((r) => r.status === 'uploaded' || r.status === 'parsing');

  // Handle setting updates
  const handleSettingsChange = (field: keyof DeckSettings, value: any) => {
    const updated = { ...settings, [field]: value };
    setSettings(updated);
    api.updateDeck(deck.id, { settings: updated }).then(onDeckUpdated).catch(console.error);
  };

  const handleTitleBlur = () => {
    if (briefTitle.trim() && briefTitle !== deck.title) {
      api.updateDeck(deck.id, { title: briefTitle }).then(onDeckUpdated).catch(console.error);
    }
  };

  const handleFilesSelected = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setUploadError(null);

    try {
      await api.uploadResources(deck.id, Array.from(files));
      onResourcesChanged();
    } catch (err: any) {
      setUploadError(err.message || 'File upload failed');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteResource = async (resId: string) => {
    try {
      await api.deleteResource(resId);
      onResourcesChanged();
    } catch (err: any) {
      alert(err.message || 'Failed to delete resource');
    }
  };

  const handleGeneratePlan = async () => {
    if (!briefTitle.trim() || isAnyFileParsing || isGenerating) return;
    setIsGenerating(true);
    try {
      await api.generatePlan(deck.id);
      onProceedToPlan();
    } catch (err: any) {
      alert(err.message || 'Failed to start plan generation');
      setIsGenerating(false);
    }
  };

  const renderFileIcon = (kind: string) => {
    switch (kind) {
      case 'image':
        return <ImageIcon className="w-5 h-5 text-emerald-500" />;
      case 'pdf':
        return <FileText className="w-5 h-5 text-rose-500" />;
      case 'docx':
      case 'pptx':
        return <FileSpreadsheet className="w-5 h-5 text-blue-500" />;
      default:
        return <FileCode className="w-5 h-5 text-amber-500" />;
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-6 space-y-8">
      {/* Title & Idea Brief */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <label className="text-sm font-semibold text-slate-800 tracking-tight">Presentation Brief & Title</label>
          <span className="text-xs text-slate-400">The core takeaway and topic</span>
        </div>
        <textarea
          value={briefTitle}
          onChange={(e) => setBriefTitle(e.target.value)}
          onBlur={handleTitleBlur}
          placeholder="e.g. Modern Distributed Event-Driven Architecture Overview..."
          rows={3}
          className="w-full text-base font-medium text-slate-900 border border-slate-200 rounded-xl p-3.5 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 transition-all resize-none shadow-inner"
        />
      </div>

      {/* Presentation Settings Matrix */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-6">
        <h3 className="text-sm font-semibold text-slate-800 tracking-tight border-b border-slate-100 pb-3">
          Audience & Strategy Settings
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Slide Count */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-700">Slide Count</label>
              <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isAutoSlideCount}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setIsAutoSlideCount(checked);
                    handleSettingsChange('slide_count', checked ? null : 6);
                  }}
                  className="rounded text-brand-600 focus:ring-brand-500"
                />
                Auto (6–12)
              </label>
            </div>
            {!isAutoSlideCount ? (
              <input
                type="number"
                min={3}
                max={30}
                value={settings.slide_count || 6}
                onChange={(e) => handleSettingsChange('slide_count', parseInt(e.target.value, 10))}
                className="w-full text-xs font-medium border border-slate-200 rounded-lg p-2.5 focus:ring-2 focus:ring-brand-500/20 outline-none"
              />
            ) : (
              <div className="text-xs text-slate-400 border border-dashed border-slate-200 rounded-lg p-2.5 bg-slate-50">
                AI strategizes optimal count automatically
              </div>
            )}
          </div>

          {/* Tone */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-700">Tone</label>
            <select
              value={settings.tone}
              onChange={(e) => handleSettingsChange('tone', e.target.value)}
              className="w-full text-xs font-medium border border-slate-200 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-brand-500/20 outline-none"
            >
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
              <option value="technical">Technical</option>
              <option value="persuasive">Persuasive</option>
              <option value="playful">Playful</option>
            </select>
          </div>

          {/* Diagram Intensity */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-700">Diagram Intensity</label>
            <select
              value={settings.diagram_intensity}
              onChange={(e) => handleSettingsChange('diagram_intensity', e.target.value)}
              className="w-full text-xs font-medium border border-slate-200 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-brand-500/20 outline-none"
            >
              <option value="low">Low (~25% diagrams)</option>
              <option value="medium">Medium (~50% diagrams)</option>
              <option value="high">High (~75% diagrams)</option>
            </select>
          </div>

          {/* Density */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-700">Content Density</label>
            <select
              value={settings.density}
              onChange={(e) => handleSettingsChange('density', e.target.value)}
              className="w-full text-xs font-medium border border-slate-200 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-brand-500/20 outline-none"
            >
              <option value="light">Light (clean & spacious)</option>
              <option value="standard">Standard (balanced)</option>
              <option value="dense">Dense (information-rich)</option>
            </select>
          </div>

          {/* Target Audience */}
          <div className="space-y-2 md:col-span-2">
            <label className="text-xs font-medium text-slate-700">Target Audience</label>
            <input
              type="text"
              value={settings.audience}
              onChange={(e) => handleSettingsChange('audience', e.target.value)}
              placeholder="e.g. Executive leadership, Engineering team, Investors..."
              className="w-full text-xs font-medium border border-slate-200 rounded-lg p-2.5 focus:ring-2 focus:ring-brand-500/20 outline-none"
            />
          </div>

          {/* Extra Instructions */}
          <div className="space-y-2 md:col-span-2">
            <label className="text-xs font-medium text-slate-700">Extra AI Instructions (Optional)</label>
            <input
              type="text"
              value={settings.extra_instructions || ''}
              onChange={(e) => handleSettingsChange('extra_instructions', e.target.value)}
              placeholder="e.g. Focus on scalability challenges; use clear trade-off comparisons..."
              className="w-full text-xs font-medium border border-slate-200 rounded-lg p-2.5 focus:ring-2 focus:ring-brand-500/20 outline-none"
            />
          </div>
        </div>
      </div>

      {/* File Ingestion & Drag-and-Drop */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <label className="text-sm font-semibold text-slate-800 tracking-tight">Source Documents & Notes</label>
          <span className="text-xs text-slate-400">PDF, DOCX, PPTX, Markdown, Text, Images</span>
        </div>

        {uploadError && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{uploadError}</span>
          </div>
        )}

        {/* Drop zone */}
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.stopPropagation();
            handleFilesSelected(e.dataTransfer.files);
          }}
          className="border-2 border-dashed border-slate-200 hover:border-brand-400 rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-50/50 hover:bg-brand-50/20 group"
        >
          <input
            type="file"
            ref={fileInputRef}
            multiple
            onChange={(e) => handleFilesSelected(e.target.files)}
            className="hidden"
            accept=".pdf,.docx,.pptx,.md,.txt,.png,.jpg,.jpeg,.webp"
          />
          <div className="w-12 h-12 rounded-full bg-slate-100 group-hover:bg-brand-100 flex items-center justify-center mb-3 transition-colors">
            <Upload className="w-5 h-5 text-slate-500 group-hover:text-brand-600 transition-colors" />
          </div>
          <div className="text-xs font-semibold text-slate-800">Click to upload or drag & drop files here</div>
          <div className="text-[11px] text-slate-400 mt-1">Up to 25MB per file</div>
        </div>

        {/* Resource List */}
        {resources.length > 0 && (
          <div className="space-y-3 pt-2">
            <h4 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Uploaded Resources ({resources.length})</h4>
            <div className="grid grid-cols-1 gap-2.5">
              {resources.map((res) => (
                <div
                  key={res.id}
                  className="flex items-center justify-between p-3 rounded-xl border border-slate-200/90 bg-white hover:border-slate-300 transition-all shadow-xs"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2 rounded-lg bg-slate-50 shrink-0">
                      {renderFileIcon(res.kind)}
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-slate-800 truncate">{res.filename}</div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                        <span>{(res.size / 1024).toFixed(1)} KB</span>
                        <span>•</span>
                        {res.status === 'parsing' || res.status === 'uploaded' ? (
                          <span className="flex items-center gap-1 text-amber-600 font-medium">
                            <Loader2 className="w-3 h-3 animate-spin" />
                            Parsing...
                          </span>
                        ) : res.status === 'parsed' ? (
                          <span className="flex items-center gap-1 text-emerald-600 font-medium">
                            <CheckCircle2 className="w-3 h-3" />
                            Parsed
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-rose-600 font-medium" title={res.error || 'Parsing error'}>
                            <AlertCircle className="w-3 h-3" />
                            Failed
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right tools: thumbnails preview or delete */}
                  <div className="flex items-center gap-3">
                    {res.images && res.images.length > 0 && (
                      <div className="flex items-center -space-x-1.5 overflow-hidden">
                        {res.images.slice(0, 3).map((img) => (
                          <img
                            key={img.id}
                            src={`/api/assets/${img.asset_id}`}
                            alt={img.caption || 'Thumbnail'}
                            title={img.caption || 'Extracted image'}
                            className="w-7 h-7 object-cover rounded-full border-2 border-white shadow-xs"
                          />
                        ))}
                        {res.images.length > 3 && (
                          <span className="w-7 h-7 flex items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-600 border-2 border-white">
                            +{res.images.length - 3}
                          </span>
                        )}
                      </div>
                    )}

                    <button
                      onClick={() => handleDeleteResource(res.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                      title="Remove resource"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Generate Button Footer */}
      <div className="flex items-center justify-end pt-4">
        <button
          onClick={handleGeneratePlan}
          disabled={!briefTitle.trim() || isAnyFileParsing || isGenerating}
          className={`flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white shadow-md transition-all ${
            !briefTitle.trim() || isAnyFileParsing || isGenerating
              ? 'bg-slate-300 cursor-not-allowed shadow-none'
              : 'bg-brand-600 hover:bg-brand-700 active:scale-98 shadow-brand-500/20'
          }`}
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Generating Presentation Plan...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Generate Presentation Plan</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
