/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useCallback, useMemo, useState } from 'react';
import ToastContainer from '@/components/Toast/ToastContainer';

const ToastContext = createContext(null);
let toastId = 0;

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, message, type, duration }]);
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const value = useMemo(
    () => ({
      success: (m, d) => addToast(m, 'success', d),
      error: (m, d) => addToast(m, 'error', d),
      warning: (m, d) => addToast(m, 'warning', d),
      info: (m, d) => addToast(m, 'info', d),
    }),
    [addToast],
  );

  return (
    <ToastContext.Provider value={value}>
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      {children}
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
};
