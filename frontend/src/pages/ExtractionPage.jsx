import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useExtraction } from '../hooks/useExtraction';
import { ArrowLeft } from 'lucide-react';
import ExtractionCard from '../components/ExtractionCard';
import ExtractionDetails from '../components/ExtractionDetails';

export default function ExtractionPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { extractions, selectedExtraction, getCurrentExtraction, deleteExtraction, setSelectedExtraction } = useExtraction();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const currentExtraction = getCurrentExtraction();

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
        {extractions.length === 0 ? (
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
                      isSelected={selectedExtraction === extraction.id}
                      onSelect={() => setSelectedExtraction(extraction.id)}
                      onDelete={deleteExtraction}
                    />
                  ))}
                </div>
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
