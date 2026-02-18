import { Trash2, Eye } from 'lucide-react';

export default function ExtractionCard({ extraction, isSelected, onSelect, onDelete }) {
  return (
    <div
      onClick={onSelect}
      className={`p-4 rounded-lg border cursor-pointer transition-all duration-200 ${
        isSelected
          ? 'border-surface-light bg-hover shadow-lg'
          : 'border-border bg-secondary hover:border-surface-light hover:shadow-md'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-semibold text-light truncate">{extraction.image_name}</h3>
          <p className="text-xs text-text-secondary">
            {new Date(extraction.timestamp).toLocaleDateString()} {new Date(extraction.timestamp).toLocaleTimeString()}
          </p>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(extraction.id);
          }}
          className="text-text-secondary hover:text-error transition-colors"
        >
          <Trash2 size={18} />
        </button>
      </div>

      <p className="text-sm text-text-secondary line-clamp-2 mb-3">{extraction.caption}</p>

      {/* Objects */}
      {extraction.objects && extraction.objects.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-semibold text-text-secondary mb-1">Detected Objects:</p>
          <div className="flex flex-wrap gap-1">
            {extraction.objects.slice(0, 3).map((obj, idx) => (
              <span key={idx} className="px-2 py-1 bg-surface-light text-light text-xs rounded">
                {obj}
              </span>
            ))}
            {extraction.objects.length > 3 && (
              <span className="px-2 py-1 text-text-secondary text-xs">+{extraction.objects.length - 3}</span>
            )}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-border">
        <div className="text-xs text-text-secondary">
          {extraction.objects?.length || 0} objects • {extraction.ocr_text?.length > 0 ? 'OCR' : 'No OCR'}
        </div>
        {isSelected && (
          <Eye size={16} className="text-text-secondary" />
        )}
      </div>
    </div>
  );
}
