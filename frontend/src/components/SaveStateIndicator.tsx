import { AlertCircle, CheckCircle2, Loader2, RefreshCw } from 'lucide-react';
import React from 'react';
import { SaveStatus } from '../types';

interface Props {
  status: SaveStatus;
  errorMessage?: string | null;
  onRetry?: () => void;
}

export const SaveStateIndicator: React.FC<Props> = ({ status, errorMessage, onRetry }) => {
  if (status === 'saving') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-amber-600 font-medium px-2 py-1 rounded bg-amber-50 border border-amber-200">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        <span>Saving...</span>
      </div>
    );
  }

  if (status === 'conflict') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-rose-700 font-medium px-2 py-1 rounded bg-rose-50 border border-rose-200">
        <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
        <span>Draft Conflict</span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="ml-1 underline hover:text-rose-900 font-semibold"
          >
            Reload
          </button>
        )}
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-red-600 font-medium px-2 py-1 rounded bg-red-50 border border-red-200">
        <AlertCircle className="w-3.5 h-3.5" />
        <span title={errorMessage || undefined}>Save Failed</span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="ml-1 p-0.5 hover:bg-red-100 rounded text-red-700"
            title="Retry save"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium px-2 py-1">
      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
      <span>Saved</span>
    </div>
  );
};
