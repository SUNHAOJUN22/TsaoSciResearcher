import { useState, useCallback, useEffect } from 'react';
import { safeStorage } from '@/lib/utils';

export function useColumnResizing(defaultWidths: Record<string, number>) {
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(() => {
    const saved = safeStorage.local.getItem('resindb-column-widths');
    if (saved) {
      try {
        return { ...defaultWidths, ...JSON.parse(saved) };
      } catch {
        return defaultWidths;
      }
    }
    return defaultWidths;
  });

  useEffect(() => {
    const handler = setTimeout(() => {
      safeStorage.local.setItem('resindb-column-widths', JSON.stringify(columnWidths));
    }, 500);
    return () => clearTimeout(handler);
  }, [columnWidths]);

  const handleResize = useCallback((key: string, newWidth: number) => {
    setColumnWidths(prev => ({
      ...prev,
      [key]: Math.max(newWidth, 60) // Minimum width
    }));
  }, []);

  return {
    columnWidths,
    handleResize
  };
}
