/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useEffect, useState } from 'react';

export const ExtractionContext = createContext();

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';
const extractionPathPrefixes = ['', '/features', '/api'];

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

const parseExtractionsPayload = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.extractions)) return payload.extractions;
  return [];
};

export function ExtractionProvider({ children }) {
  const [extractions, setExtractions] = useState([]);
  const [selectedExtraction, setSelectedExtraction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activePathPrefix, setActivePathPrefix] = useState('');

  const getCurrentExtraction = useCallback(() => {
    return extractions.find(e => e.id === selectedExtraction);
  }, [extractions, selectedExtraction]);

  const refreshExtractions = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      let lastError = null;
      let payload = [];
      let didLoad = false;
      let firstSuccessfulPrefix = '';
      let firstSuccessfulPayload = [];

      for (const prefix of extractionPathPrefixes) {
        try {
          const response = await fetch(`${apiBaseUrl}${prefix}/extractions`);
          const parsedPayload = await response.json().catch(() => []);

          if (!response.ok) {
            const message = parsedPayload?.error || `Failed to load extractions (${response.status})`;
            if (response.status === 404) {
              lastError = new Error(message);
              continue;
            }
            throw new Error(message);
          }

          const parsedRows = parseExtractionsPayload(parsedPayload);
          if (!didLoad) {
            firstSuccessfulPrefix = prefix;
            firstSuccessfulPayload = parsedRows;
            didLoad = true;
          }
          if (parsedRows.length > 0) {
            payload = parsedRows;
            setActivePathPrefix(prefix);
            break;
          }
        } catch (innerErr) {
          lastError = innerErr;
        }
      }

      if (!didLoad) {
        throw lastError || new Error('Failed to load extractions');
      }
      if (payload.length === 0) {
        payload = firstSuccessfulPayload;
        setActivePathPrefix(firstSuccessfulPrefix);
      }

      const normalized = payload.map(normalizeExtraction);

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
    const prefixesToTry = [activePathPrefix, ...extractionPathPrefixes.filter(prefix => prefix !== activePathPrefix)];
    let response = null;
    let lastError = null;

    for (const prefix of prefixesToTry) {
      try {
        response = await fetch(`${apiBaseUrl}${prefix}/extractions/${id}`, {
          method: 'DELETE',
        });

        if (response.status === 404) {
          lastError = new Error('Extraction not found');
          continue;
        }

        setActivePathPrefix(prefix);
        break;
      } catch (err) {
        lastError = err;
      }
    }

    if (!response) {
      throw lastError || new Error('Failed to delete extraction');
    }

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
  }, [activePathPrefix]);

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
