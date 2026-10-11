import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  Check,
  CheckCircle,
  GripVertical,
  ImageIcon,
  Loader2,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
} from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { api } from '../../api/client';
import { Deck, DiagramHint, PlanContent, PlanRecord, PlanSlide, Resource } from '../../types';

interface PlanStepProps {
  deckId: string;
  resources: Resource[];
  deck?: Deck | null;
  onPlanApproved: () => void;
  onBackToBrief?: () => void;
}

export const PlanStep: React.FC<PlanStepProps> = ({ deckId, resources, deck, onPlanApproved, onBackToBrief }) => {
  const [planRecord, setPlanRecord] = useState<PlanRecord | null>(null);
  const [plan, setPlan] = useState<PlanContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'error'>('saved');
  const [feedback, setFeedback] = useState('');
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [showRegenConfirm, setShowRegenConfirm] = useState(false);

  // Debounced auto-save ref
  const saveTimeoutRef = useRef<any>(null);

  // Collect all available images across resources
  const availableImages = resources.flatMap((r) => r.images || []);

  useEffect(() => {
    let isMounted = true;
    let pollTimer: any = null;

    const fetchPlan = async () => {
      try {
        const p = await api.getPlan(deckId);
        if (isMounted) {
          setPlanRecord(p);
          setPlan(p.content);
          setLoading(false);
        }
      } catch (err) {
        // Continue polling if plan is not ready yet
        if (isMounted) {
          pollTimer = setTimeout(fetchPlan, 1500);
        }
      }
    };

    fetchPlan();

    return () => {
      isMounted = false;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [deckId, deck?.current_plan_id]);

  // Debounced save when plan changes
  const queueSave = (newPlan: PlanContent) => {
    setPlan(newPlan);
    setSaveStatus('saving');
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);

    saveTimeoutRef.current = setTimeout(async () => {
      try {
        const saved = await api.updatePlan(deckId, newPlan);
        setPlanRecord(saved);
        setSaveStatus('saved');
      } catch (err) {
        console.error('Auto-save plan failed:', err);
        setSaveStatus('error');
      }
    }, 800);
  };

  const handleUpdateSlide = (index: number, updates: Partial<PlanSlide>) => {
    if (!plan) return;
    const slides = [...plan.slides];
    slides[index] = { ...slides[index], ...updates };
    queueSave({ ...plan, slides });
  };

  const handleMoveSlide = (index: number, direction: 'up' | 'down') => {
    if (!plan) return;
    const targetIdx = direction === 'up' ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= plan.slides.length) return;

    const slides = [...plan.slides];
    const temp = slides[index];
    slides[index] = slides[targetIdx];
    slides[targetIdx] = temp;

    // Keep keys consistent
    slides.forEach((s, idx) => {
      s.key = `s${idx + 1}`;
    });

    queueSave({ ...plan, slides });
  };

  const handleDeleteSlide = (index: number) => {
    if (!plan || plan.slides.length <= 1) {
      alert('A presentation must have at least one slide.');
      return;
    }
    const slides = plan.slides.filter((_, idx) => idx !== index);
    slides.forEach((s, idx) => {
      s.key = `s${idx + 1}`;
    });
    queueSave({ ...plan, slides });
  };

  const handleAddSlide = () => {
    if (!plan) return;
    const newIdx = plan.slides.length + 1;
    const newSlide: PlanSlide = {
      key: `s${newIdx}`,
      role: 'content',
      title: 'New Slide Point',
      kind: 'text',
      layout_hint: 'text',
      key_points: ['Key argument or explanation point'],
      image_ids: [],
      intent: 'Explain key idea',
    };
    queueSave({ ...plan, slides: [...plan.slides, newSlide] });
  };

  const handleRegenerate = async () => {
    setShowRegenConfirm(false);
    setIsRegenerating(true);
    try {
      await api.regeneratePlan(deckId, feedback);
      // Wait for SSE or poll
    } catch (err: any) {
      alert(err.message || 'Regenerate plan failed');
      setIsRegenerating(false);
    }
  };

  const handleApprove = async () => {
    if (!plan) return;
    setIsApproving(true);
    try {
      await api.approvePlan(deckId);
      onPlanApproved();
    } catch (err: any) {
      alert(err.message || 'Approve plan failed');
      setIsApproving(false);
    }
  };

  if (deck?.status === 'failed' && !plan) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4 max-w-md mx-auto text-center">
        <AlertCircle className="w-10 h-10 text-rose-500" />
        <div className="text-base font-semibold text-slate-800">Plan Generation Failed</div>
        <div className="text-xs text-slate-500">
          The background job encountered an error while generating the presentation plan.
        </div>
        {onBackToBrief && (
          <button
            onClick={onBackToBrief}
            className="px-4 py-2 bg-brand-600 text-white rounded-xl text-xs font-semibold hover:bg-brand-700 transition-colors shadow-sm"
          >
            Back to Brief
          </button>
        )}
      </div>
    );
  }

  if (loading || !plan) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4">
        <Loader2 className="w-9 h-9 text-brand-600 animate-spin" />
        <div className="text-sm font-semibold text-slate-800">Generating presentation plan...</div>
        <div className="text-xs text-slate-400">Analyzing brief and structuring slide outline</div>
        {onBackToBrief && (
          <button
            onClick={onBackToBrief}
            className="mt-3 text-xs text-slate-500 hover:text-slate-800 underline transition-colors"
          >
            Cancel and return to brief
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-6 space-y-8">
      {/* Top Banner & Status */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-bold text-slate-900 tracking-tight">{plan.title}</h2>
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
              v{planRecord?.version || 1}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 line-clamp-2">{plan.narrative_summary}</p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
            {saveStatus === 'saving' ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin text-brand-600" />
                <span>Saving edits...</span>
              </>
            ) : saveStatus === 'saved' ? (
              <>
                <Check className="w-3 h-3 text-emerald-600" />
                <span>Saved</span>
              </>
            ) : (
              <span className="text-rose-500">Save failed</span>
            )}
          </div>

          <button
            onClick={handleApprove}
            disabled={isApproving}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold shadow-sm transition-all active:scale-98"
          >
            {isApproving ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Generating Slides...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Approve & Generate Slides</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Slide Cards Outline */}
      <div className="space-y-4">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Slide Outline ({plan.slides.length} slides)
          </h3>
          <button
            onClick={handleAddSlide}
            className="flex items-center gap-1.5 text-xs font-semibold text-brand-600 hover:text-brand-700 bg-brand-50 hover:bg-brand-100/70 px-3 py-1.5 rounded-lg transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Slide</span>
          </button>
        </div>

        {plan.slides.map((slide, idx) => (
          <div
            key={slide.key}
            className="bg-white rounded-2xl p-5 border border-slate-200/90 hover:border-slate-300 transition-all shadow-xs space-y-4"
          >
            {/* Card Header */}
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-lg bg-slate-100 text-slate-700 font-bold text-xs flex items-center justify-center shrink-0">
                  {idx + 1}
                </span>

                <input
                  type="text"
                  value={slide.title}
                  onChange={(e) => handleUpdateSlide(idx, { title: e.target.value })}
                  placeholder="Slide Assertion / Title"
                  className="text-sm font-bold text-slate-900 border-b border-transparent hover:border-slate-200 focus:border-brand-500 focus:outline-none px-1 py-0.5 transition-colors w-full max-w-lg"
                />
              </div>

              {/* Top controls: Role, Kind, Move, Delete */}
              <div className="flex items-center gap-2 shrink-0">
                {/* Role badge select */}
                <select
                  value={slide.role}
                  onChange={(e) => handleUpdateSlide(idx, { role: e.target.value as any })}
                  className="text-[11px] font-semibold bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-slate-700 outline-none"
                >
                  <option value="cover">Cover</option>
                  <option value="agenda">Agenda</option>
                  <option value="section">Section</option>
                  <option value="content">Content</option>
                  <option value="process">Process</option>
                  <option value="comparison">Comparison</option>
                  <option value="data">Data</option>
                  <option value="summary">Summary</option>
                  <option value="closing">Closing</option>
                </select>

                {/* Kind Toggle */}
                <div className="flex items-center bg-slate-100 p-0.5 rounded-lg text-[11px] font-medium text-slate-600">
                  <button
                    onClick={() => handleUpdateSlide(idx, { kind: 'text' })}
                    className={`px-2 py-0.5 rounded-md transition-colors ${slide.kind === 'text' ? 'bg-white text-brand-700 shadow-2xs font-semibold' : ''}`}
                  >
                    Text
                  </button>
                  <button
                    onClick={() =>
                      handleUpdateSlide(idx, {
                        kind: 'diagram',
                        diagram_hint: slide.diagram_hint || { kind: 'flow', description: 'Flow diagram' },
                      })
                    }
                    className={`px-2 py-0.5 rounded-md transition-colors ${slide.kind === 'diagram' ? 'bg-white text-brand-700 shadow-2xs font-semibold' : ''}`}
                  >
                    Diagram
                  </button>
                  <button
                    onClick={() =>
                      handleUpdateSlide(idx, {
                        kind: 'hybrid',
                        diagram_hint: slide.diagram_hint || { kind: 'flow', description: 'Flow diagram' },
                      })
                    }
                    className={`px-2 py-0.5 rounded-md transition-colors ${slide.kind === 'hybrid' ? 'bg-white text-brand-700 shadow-2xs font-semibold' : ''}`}
                  >
                    Hybrid
                  </button>
                </div>

                {/* Move up / down */}
                <button
                  onClick={() => handleMoveSlide(idx, 'up')}
                  disabled={idx === 0}
                  className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-30 rounded transition-colors"
                >
                  <ArrowUp className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => handleMoveSlide(idx, 'down')}
                  disabled={idx === plan.slides.length - 1}
                  className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-30 rounded transition-colors"
                >
                  <ArrowDown className="w-3.5 h-3.5" />
                </button>

                {/* Delete slide */}
                <button
                  onClick={() => handleDeleteSlide(idx)}
                  className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                  title="Delete slide"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Diagram Hint settings if diagram or hybrid */}
            {(slide.kind === 'diagram' || slide.kind === 'hybrid') && (
              <div className="bg-slate-50/80 rounded-xl p-3 border border-slate-200/70 flex flex-col md:flex-row items-center gap-3">
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[11px] font-semibold text-slate-600">Diagram:</span>
                  <select
                    value={slide.diagram_hint?.kind || 'flow'}
                    onChange={(e) =>
                      handleUpdateSlide(idx, {
                        diagram_hint: {
                          kind: e.target.value as any,
                          description: slide.diagram_hint?.description || 'Relationship diagram',
                        },
                      })
                    }
                    className="text-xs font-semibold bg-white border border-slate-200 rounded-lg px-2 py-1 outline-none"
                  >
                    <option value="flow">Flow</option>
                    <option value="hierarchy">Hierarchy</option>
                    <option value="layers">Layers</option>
                    <option value="cycle">Cycle</option>
                    <option value="timeline">Timeline</option>
                    <option value="comparison">Comparison</option>
                    <option value="mindmap">Mindmap</option>
                  </select>
                </div>

                <input
                  type="text"
                  value={slide.diagram_hint?.description || ''}
                  onChange={(e) =>
                    handleUpdateSlide(idx, {
                      diagram_hint: {
                        kind: slide.diagram_hint?.kind || 'flow',
                        description: e.target.value,
                      },
                    })
                  }
                  placeholder="Describe nodes and relations (e.g. Data flows from Client to Bus to Workers)..."
                  className="w-full text-xs bg-white border border-slate-200 rounded-lg px-2.5 py-1 focus:ring-1 focus:ring-brand-500 outline-none"
                />
              </div>
            )}

            {/* Key Points */}
            <div className="space-y-2">
              <label className="text-[11px] font-semibold text-slate-600">Key Points / Takeaways</label>
              <div className="space-y-1.5">
                {slide.key_points.map((pt, ptIdx) => (
                  <div key={ptIdx} className="flex items-center gap-2">
                    <span className="text-slate-300 font-bold">•</span>
                    <input
                      type="text"
                      value={pt}
                      onChange={(e) => {
                        const newPts = [...slide.key_points];
                        newPts[ptIdx] = e.target.value;
                        handleUpdateSlide(idx, { key_points: newPts });
                      }}
                      className="w-full text-xs border border-slate-200/80 rounded-lg px-2.5 py-1 focus:ring-1 focus:ring-brand-500 outline-none"
                    />
                    <button
                      onClick={() => {
                        const newPts = slide.key_points.filter((_, i) => i !== ptIdx);
                        handleUpdateSlide(idx, { key_points: newPts });
                      }}
                      className="p-1 text-slate-300 hover:text-rose-500 transition-colors"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => {
                    handleUpdateSlide(idx, { key_points: [...slide.key_points, ''] });
                  }}
                  className="text-[11px] font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1 pt-1"
                >
                  <Plus className="w-3 h-3" />
                  <span>Add Key Point</span>
                </button>
              </div>
            </div>

            {/* Image Attachments from Available Catalog */}
            {availableImages.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <label className="text-[11px] font-semibold text-slate-600 flex items-center gap-1.5">
                  <ImageIcon className="w-3.5 h-3.5 text-slate-400" />
                  <span>Attached Image Assets</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableImages.map((img) => {
                    const isAttached = slide.image_ids.includes(img.asset_id);
                    return (
                      <button
                        key={img.id}
                        type="button"
                        onClick={() => {
                          const newIds = isAttached
                            ? slide.image_ids.filter((id) => id !== img.asset_id)
                            : [...slide.image_ids, img.asset_id];
                          handleUpdateSlide(idx, { image_ids: newIds });
                        }}
                        className={`flex items-center gap-2 p-1.5 pr-2.5 rounded-lg border text-xs transition-all ${
                          isAttached
                            ? 'border-brand-500 bg-brand-50/50 text-brand-700 font-medium'
                            : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                        }`}
                      >
                        <img
                          src={`/api/assets/${img.asset_id}`}
                          alt={img.caption || 'Thumbnail'}
                          className="w-5 h-5 object-cover rounded"
                        />
                        <span className="truncate max-w-[140px] text-[11px]">{img.caption || img.asset_id.slice(0, 8)}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Regenerate Plan Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-3">
        <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">AI Plan Revision</h4>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="e.g. Focus more on technical architecture in slide 2; make slide 4 a cycle diagram..."
          rows={2}
          className="w-full text-xs border border-slate-200 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
        />

        <div className="flex items-center justify-between pt-1">
          <span className="text-[11px] text-slate-400">Your current outline edits will be provided as the revision baseline.</span>
          <button
            onClick={() => setShowRegenConfirm(true)}
            disabled={isRegenerating}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl border border-slate-200 hover:border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
            <span>Regenerate Plan</span>
          </button>
        </div>
      </div>

      {/* Confirm Modal */}
      {showRegenConfirm && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-xl border border-slate-100">
            <h3 className="text-sm font-bold text-slate-900">Confirm Plan Regeneration</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              This will create a new AI plan version incorporating your feedback and current edits. Are you sure you want to proceed?
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setShowRegenConfirm(false)}
                className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleRegenerate}
                className="px-3.5 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold"
              >
                Proceed
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
