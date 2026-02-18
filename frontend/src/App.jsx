import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ChatProvider } from './context/ChatContext';
import { ExtractionProvider } from './context/ExtractionContext';
import AuthPage from './pages/AuthPage';
import ChatPage from './pages/ChatPage';
import ExtractionPage from './pages/ExtractionPage';
import './index.css';

function App() {
  return (
    <Router>
      <AuthProvider>
        <ChatProvider>
          <ExtractionProvider>
            <Routes>
              <Route path="/" element={<AuthPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/extractions" element={<ExtractionPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </ExtractionProvider>
        </ChatProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
