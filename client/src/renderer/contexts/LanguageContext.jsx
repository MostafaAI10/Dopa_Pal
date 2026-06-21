import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { translations } from '../locales';

const LanguageContext = createContext();
const RTL_LANGS = new Set(['ar', 'fa', 'ur', 'he']);

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    // Try local storage first for instant load
    return localStorage.getItem('dopapal_lang') || 'ar';
  });

  // Fetch language from backend on mount
  useEffect(() => {
    api.getUserSettings()
      .then(data => {
        if (data?.language) {
          setLang(data.language);
          localStorage.setItem('dopapal_lang', data.language);
        }
      })
      .catch(() => {
        // Use localStorage fallback silently
      });
  }, []);

  // Apply dir attribute + font on lang change
  useEffect(() => {
    document.documentElement.setAttribute('dir', RTL_LANGS.has(lang) ? 'rtl' : 'ltr');
    document.documentElement.setAttribute('lang', lang);
  }, [lang]);

  const changeLanguage = useCallback(async (newLang) => {
    setLang(newLang);
    localStorage.setItem('dopapal_lang', newLang);
    try {
      await api.updateUserSettings({ language: newLang });
    } catch (e) {
      console.warn('Could not persist language to backend:', e);
    }
  }, []);

  // Translation function
  const t = useCallback((key, fallback) => {
    const dict = translations[lang] || translations['en'];
    return dict[key] ?? fallback ?? key;
  }, [lang]);

  return (
      <LanguageContext.Provider value={{ lang, changeLanguage, t, isRTL: RTL_LANGS.has(lang) }}>
        {children}
      </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used inside <LanguageProvider>');
  return ctx;
}
