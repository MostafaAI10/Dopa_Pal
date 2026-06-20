import React from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import Bubble    from './components/Bubble/Bubble';
import Dashboard from './components/Dashboard/Dashboard';
import { LanguageProvider } from './contexts/LanguageContext';

const App = () => (
  <LanguageProvider>
    <HashRouter>
      <Routes>
        <Route path="/"          element={<Bubble    />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </HashRouter>
  </LanguageProvider>
);

export default App;
