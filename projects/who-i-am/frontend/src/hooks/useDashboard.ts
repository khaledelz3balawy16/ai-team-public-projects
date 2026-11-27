import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { DashboardResponse } from '../types/assessment';

interface State {
  data:    DashboardResponse | null;
  loading: boolean;
  error:   string | null;
}

export function useDashboard() {
  const [state, setState] = useState<State>({ data: null, loading: true, error: null });

  const refetch = async () => {
    // Keep existing data visible during refresh — prevents scroll-to-top
    setState(s => ({ ...s, loading: s.data === null, error: null }));
    try {
      const data = await api.getDashboard();
      setState({ data, loading: false, error: null });
    } catch (err) {
      setState(s => ({ ...s, loading: false, error: String(err) }));
    }
  };

  useEffect(() => { void refetch(); }, []);

  return { ...state, refetch };
}
