import React from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { CalibratePage } from './dev/CalibratePage';
import { CompilerPage } from './dev/CompilerPage';
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
        <Route path="/dev/compiler" element={<CompilerPage />} />
        <Route path="/dev/calibrate" element={<CalibratePage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
