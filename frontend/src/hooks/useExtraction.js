import { useContext } from 'react';
import { ExtractionContext } from '../context/ExtractionContext';

export function useExtraction() {
  const context = useContext(ExtractionContext);
  if (!context) {
    throw new Error('useExtraction must be used within an ExtractionProvider');
  }
  return context;
}
