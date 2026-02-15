import { useChat } from '../hooks/useChat';
import { Zap } from 'lucide-react';

const models = [
  { id: 'normal', label: 'Normal', description: 'Standard vision analysis' },
  { id: 'yolo', label: 'YOLO', description: 'Real-time object detection' },
  { id: 'clip', label: 'CLIP', description: 'Vision-language understanding' },
  { id: 'custom', label: 'Custom', description: 'Custom trained model' }
];

export default function ModelSelector() {
  const { selectedModel, setSelectedModel } = useChat();

  return (
    <div className="p-4 bg-white rounded-lg border border-border shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Zap className="text-primary" size={20} />
        <h3 className="font-semibold text-dark">AI Model</h3>
      </div>
      
      <div className="grid grid-cols-2 gap-2">
        {models.map(model => (
          <button
            key={model.id}
            onClick={() => setSelectedModel(model.id)}
            className={`p-3 rounded-lg border transition-all duration-200 text-left ${
              selectedModel === model.id
                ? 'bg-primary border-primary text-white shadow-lg'
                : 'bg-light border-border hover:border-primary hover:bg-gray-50'
            }`}
          >
            <p className="font-semibold text-sm">{model.label}</p>
            <p className={`text-xs ${selectedModel === model.id ? 'text-blue-100' : 'text-gray-500'}`}>
              {model.description}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
