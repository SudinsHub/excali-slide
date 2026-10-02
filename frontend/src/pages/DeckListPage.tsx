import { Clock, Layout, Plus, Sparkles, Trash2 } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Deck } from '../types';

export const DeckListPage: React.FC = () => {
  const navigate = useNavigate();
  const [decks, setDecks] = useState<Deck[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  const fetchDecks = async () => {
    setIsLoading(true);
    try {
      const data = await api.getDecks();
      setDecks(data);
    } catch (err) {
      console.error('Failed to load decks:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDecks();
  }, []);

  const handleCreateDeck = async () => {
    const title = prompt('Enter a title for the new deck:', 'Untitled Presentation');
    if (!title) return;

    setIsCreating(true);
    try {
      const deck = await api.createDeck(title);
      // Create first blank slide
      await api.createBlankSlide(deck.id);
      navigate(`/decks/${deck.id}`);
    } catch (err: any) {
      alert(err.message || 'Failed to create deck');
    } finally {
      setIsCreating(false);
    }
  };

  const handleCreateSampleDeck = async () => {
    setIsCreating(true);
    try {
      const deck = await api.createSampleDeck();
      navigate(`/decks/${deck.id}`);
    } catch (err: any) {
      alert(err.message || 'Failed to create demo deck');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteDeck = async (e: React.MouseEvent, deckId: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this deck?')) {
      try {
        await api.deleteDeck(deckId);
        setDecks((prev) => prev.filter((d) => d.id !== deckId));
      } catch (err: any) {
        alert(err.message || 'Failed to delete deck');
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Navigation */}
      <header className="h-16 border-b border-slate-200 bg-white px-8 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-brand-500 text-white flex items-center justify-center font-bold text-lg shadow-sm">
            E
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 leading-none">Excalidraw Slide Studio</h1>
            <span className="text-xs text-slate-500">Editable AI Presentations</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCreateSampleDeck}
            disabled={isCreating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-amber-200 bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-semibold transition-all disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-600" />
            <span>Load Demo Fixture Deck</span>
          </button>
          <button
            onClick={handleCreateDeck}
            disabled={isCreating}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white text-xs font-semibold shadow-xs transition-all disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            <span>New Deck</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-slate-800">Your Decks</h2>
          <span className="text-xs text-slate-500">{decks.length} presentations</span>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-44 rounded-xl border border-slate-200 bg-white animate-pulse" />
            ))}
          </div>
        ) : decks.length === 0 ? (
          <div className="rounded-2xl border-2 border-dashed border-slate-200 bg-white p-12 text-center max-w-md mx-auto my-12">
            <Layout className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-700 mb-1">No decks yet</h3>
            <p className="text-xs text-slate-500 mb-4">
              Create a new presentation from scratch or try our pre-built demo deck.
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={handleCreateSampleDeck}
                className="px-3.5 py-2 rounded-lg border border-amber-300 bg-amber-50 text-amber-800 text-xs font-semibold hover:bg-amber-100"
              >
                Load Demo Deck
              </button>
              <button
                onClick={handleCreateDeck}
                className="px-3.5 py-2 rounded-lg bg-brand-500 text-white text-xs font-semibold hover:bg-brand-600"
              >
                Create Blank Deck
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            {decks.map((deck) => {
              const dateStr = new Date(deck.updated_at).toLocaleDateString([], {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              });

              return (
                <div
                  key={deck.id}
                  onClick={() => navigate(`/decks/${deck.id}`)}
                  className="group relative rounded-xl border border-slate-200 bg-white p-5 hover:border-brand-500 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <h3 className="font-semibold text-slate-800 text-sm group-hover:text-brand-600 transition-colors line-clamp-1">
                        {deck.title}
                      </h3>
                      <button
                        onClick={(e) => handleDeleteDeck(e, deck.id)}
                        className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-all"
                        title="Delete deck"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-500 mb-6">
                      <span className="flex items-center gap-1 font-medium bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                        <Layout className="w-3 h-3" />
                        {deck.slide_count} slides
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {dateStr}
                      </span>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-brand-600 font-semibold">
                    <span>Open Editor</span>
                    <span className="group-hover:translate-x-0.5 transition-transform">→</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
};
