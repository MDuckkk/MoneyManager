import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import AppProviders from '@/app/providers/AppProviders';
import App from './App.jsx';
import './index.css';

// Áp dụng theme đã lưu trước khi render để tránh nhấp nháy.
document.documentElement.setAttribute('data-theme', localStorage.getItem('mm_theme') || 'light');

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AppProviders>
      <App />
    </AppProviders>
  </StrictMode>,
);
