import { createContext, useState } from 'react';

export const ExtractionContext = createContext();

export function ExtractionProvider({ children }) {
  const [extractions, setExtractions] = useState([
    {
      id: '1',
      image_name: 'sample_image.jpg',
      caption: 'A beautiful landscape with mountains and trees',
      objects: ['mountain', 'tree', 'sky', 'grass'],
      ocr_text: 'Sample OCR text from image',
      scene_labels: ['outdoor', 'nature', 'landscape'],
      color_features: [150, 120, 100],
      texture_features: [0.45, 0.32, 0.18],
      clip_embedding_file: 'embedding_001.npy',
      clip_embedding_path: '/embeddings/embedding_001.npy',
      timestamp: new Date(Date.now() - 86400000)
    }
  ]);

  const [selectedExtraction, setSelectedExtraction] = useState('1');

  const getCurrentExtraction = () => {
    return extractions.find(e => e.id === selectedExtraction);
  };

  const addExtraction = (data) => {
    const newExtraction = {
      ...data,
      id: Date.now().toString(),
      timestamp: new Date()
    };
    setExtractions(prev => [newExtraction, ...prev]);
    return newExtraction;
  };

  const deleteExtraction = (id) => {
    setExtractions(prev => prev.filter(e => e.id !== id));
    if (selectedExtraction === id) {
      setSelectedExtraction(extractions.length > 0 ? extractions[0].id : null);
    }
  };

  return (
    <ExtractionContext.Provider value={{
      extractions,
      selectedExtraction,
      getCurrentExtraction,
      addExtraction,
      deleteExtraction,
      setSelectedExtraction
    }}>
      {children}
    </ExtractionContext.Provider>
  );
}
