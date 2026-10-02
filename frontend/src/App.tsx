import React from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { SpikePage } from './dev/SpikePage';
import { DeckListPage } from './pages/DeckListPage';
import { DeckWorkspacePage } from './pages/DeckWorkspacePage';
import { PresentPage } from './pages/PresentPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DeckListPage />} />
        <Route path="/decks/:id" element={<DeckWorkspacePage />} />
        <Route path="/present/:id" element={<PresentPage />} />
        <Route path="/dev/spike" element={<SpikePage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
