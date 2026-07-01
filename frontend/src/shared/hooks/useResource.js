import { useCallback, useEffect, useRef, useState } from 'react';
import { useToast } from '@/contexts/ToastContext';

/**
 * Tải dữ liệu từ một loader async, quản lý loading/error + reload.
 * loader trả response envelope { data }.
 */
const useResource = (loader, { select = (r) => r?.data ?? null, silent = false } = {}) => {
  const toast = useToast();
  const loaderRef = useRef(loader);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);

  const reload = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await loaderRef.current();
      setData(select(response));
    } catch (err) {
      const msg = err.message || 'Không tải được dữ liệu';
      setError(msg);
      if (!silent) toast.error(msg);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast, silent]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, reload, setData };
};

export default useResource;
