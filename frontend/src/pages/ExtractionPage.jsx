import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import ExtractionCard from '../components/ExtractionCard';
import ExtractionDetails from '../components/ExtractionDetails';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';

const normalizeTextList = (value) => (Array.isArray(value) ? value : []);
const normalizeNumericList = (value) =>
  Array.isArray(value)
    ? value.map((entry) => Number(entry)).filter((entry) => Number.isFinite(entry))
    : [];

const normalizeExtraction = (data = {}) => ({
  id: String(data.id || ''),
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
});

export default function ExtractionPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [extractions, setExtractions] = useState([]);
  const [selectedExtractionId, setSelectedExtractionId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deletingId, setDeletingId] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const loadExtractions = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${apiBaseUrl}/extractions`);
      const payload = await response.json().catch(() => []);
      if (!response.ok) {
        throw new Error(payload?.error || `Failed to load extractions from ${apiBaseUrl}`);
      }

      const items = Array.isArray(payload) ? payload.map(normalizeExtraction) : [];
      setExtractions(items);
      setSelectedExtractionId((prev) => {
        if (items.length === 0) return '';
        if (prev && items.some((item) => item.id === prev)) return prev;
        return items[0].id;
      });
    } catch (err) {
      setError(err.message || `Failed to load extractions from ${apiBaseUrl}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadExtractions();
    }
  }, [isAuthenticated, loadExtractions]);

  const handleDeleteExtraction = useCallback(async (id) => {
    try {
      setDeletingId(id);
      setError('');
      const response = await fetch(`${apiBaseUrl}/extractions/${id}`, {
        method: 'DELETE',
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.error || 'Failed to delete extraction');
      }

      setExtractions((prev) => {
        const updated = prev.filter((item) => item.id !== id);
        setSelectedExtractionId((current) => {
          if (current && current !== id && updated.some((item) => item.id === current)) {
            return current;
          }
          return updated.length > 0 ? updated[0].id : '';
        });
        return updated;
      });
    } catch (err) {
      setError(err.message || 'Failed to delete extraction');
    } finally {
      setDeletingId('');
    }
  }, []);

  const currentExtraction = useMemo(
    () => extractions.find((item) => item.id === selectedExtractionId) || null,
    [extractions, selectedExtractionId]
  );

  return (
    <div className="min-h-screen bg-primary">
      {/* Header */}
      <div className="bg-secondary border-b border-border sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 text-light hover:text-text-secondary transition-colors font-medium"
          >
            <ArrowLeft size={20} />
            Back to Chat
          </button>
          <h1 className="text-2xl font-bold text-light">Extraction Results</h1>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {loading ? (
          <div className="bg-secondary rounded-lg border border-border p-12 text-center">
            <h2 className="text-xl font-semibold text-light mb-2">Loading Extractions...</h2>
            <p className="text-text-secondary">Fetching latest extraction results from backend.</p>
          </div>
        ) : error ? (
          <div className="bg-secondary rounded-lg border border-border p-12 text-center">
            <h2 className="text-xl font-semibold text-light mb-2">Could not load extractions</h2>
            <p className="text-text-secondary mb-4">{error}</p>
            <button
              onClick={loadExtractions}
              className="inline-flex items-center gap-2 px-6 py-2 bg-surface-light text-light rounded-lg hover:bg-hover transition-colors font-medium"
            >
              Retry
            </button>
          </div>
        ) : extractions.length === 0 ? (
          <div className="bg-secondary rounded-lg border border-border p-12 text-center">
            <h2 className="text-xl font-semibold text-light mb-2">No Extractions Yet</h2>
            <p className="text-text-secondary mb-4">
              Upload images in the chat to see extraction results here.
            </p>
            <button
              onClick={() => navigate('/chat')}
              className="inline-flex items-center gap-2 px-6 py-2 bg-surface-light text-light rounded-lg hover:bg-hover transition-colors font-medium"
            >
              Go to Chat
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-6">
            {/* Extractions List */}
            <div className="lg:col-span-1">
              <div className="bg-secondary rounded-lg border border-border p-4 sticky top-20">
                <h2 className="font-semibold text-light mb-4">Analyzed Images</h2>
                <p className="text-xs text-text-secondary mb-4">{extractions.length} extraction(s)</p>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {extractions.map(extraction => (
                    <ExtractionCard
                      key={extraction.id}
                      extraction={extraction}
                      isSelected={selectedExtractionId === extraction.id}
                      onSelect={() => setSelectedExtractionId(extraction.id)}
                      onDelete={handleDeleteExtraction}
                    />
                  ))}
                </div>
                {deletingId && (
                  <p className="text-xs text-text-secondary mt-3">
                    Deleting extraction...
                  </p>
                )}
              </div>
            </div>

            {/* Details View */}
            <div className="lg:col-span-2">
              <div className="bg-secondary rounded-lg border border-border p-6">
                <ExtractionDetails extraction={currentExtraction} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
