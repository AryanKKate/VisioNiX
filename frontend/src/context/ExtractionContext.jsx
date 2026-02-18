/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useEffect, useState } from 'react';

export const ExtractionContext = createContext();

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';

const normalizeTextList = (value) => (Array.isArray(value) ? value : []);
const normalizeNumericList = (value) =>
  Array.isArray(value)
    ? value.map((entry) => Number(entry)).filter((entry) => Number.isFinite(entry))
    : [];

const normalizeExtraction = (data = {}) => ({
  id: String(data.id ?? `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`),
  image_name: data.image_name || 'Unknown image',
  caption: data.caption || '',
  objects: normalizeTextList(data.objects),
  ocr_text: data.ocr_text || '',
  scene_labels: normalizeTextList(data.scene_labels),
  color_features: normalizeNumericList(data.color_features),
  texture_features: normalizeNumericList(data.texture_features),
  clip_embedding_file: data.clip_embedding_file || '',
  clip_embedding_path: data.clip_embedding_path || '',
  timestamp: data.timestamp || data.extracted_at || new Date().toISOString(),
  source: data.source || 'unknown',
});

export function ExtractionProvider({ children }) {
  const [extractions, setExtractions] = useState([]);
  const [selectedExtraction, setSelectedExtraction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const getCurrentExtraction = useCallback(() => {
    return extractions.find(e => e.id === selectedExtraction);
  }, [extractions, selectedExtraction]);

  const refreshExtractions = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${apiBaseUrl}/extractions`);
      const payload = await response.json().catch(() => []);
      if (!response.ok) {
        throw new Error(payload?.error || 'Failed to load extractions');
      }

      const normalized = Array.isArray(payload)
        ? payload.map(normalizeExtraction)
        : [];

      setExtractions(normalized);
      setSelectedExtraction(prevSelected => {
        if (normalized.length === 0) return null;
        if (prevSelected && normalized.some(item => item.id === prevSelected)) {
          return prevSelected;
        }
        return normalized[0].id;
      });
    } catch (err) {
      setError(err.message || 'Failed to load extractions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshExtractions();
  }, [refreshExtractions]);

  const addExtraction = useCallback((data) => {
    const normalized = normalizeExtraction(data);
    setExtractions(prev => [normalized, ...prev.filter(item => item.id !== normalized.id)]);
    setSelectedExtraction(normalized.id);
    return normalized;
  }, []);

  const deleteExtraction = useCallback(async (id) => {
    const response = await fetch(`${apiBaseUrl}/extractions/${id}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload?.error || 'Failed to delete extraction');
    }

    setExtractions(prev => {
      const updated = prev.filter(item => item.id !== id);
      setSelectedExtraction(prevSelected => {
        if (prevSelected && prevSelected !== id && updated.some(item => item.id === prevSelected)) {
          return prevSelected;
        }
        return updated.length > 0 ? updated[0].id : null;
      });
      return updated;
    });
  }, []);

  return (
    <ExtractionContext.Provider value={{
      extractions,
      selectedExtraction,
      loading,
      error,
      getCurrentExtraction,
      refreshExtractions,
      addExtraction,
      deleteExtraction,
      setSelectedExtraction
    }}>
      {children}
    </ExtractionContext.Provider>
  );
}
