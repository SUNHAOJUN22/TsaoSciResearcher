import { useState, useCallback } from "react";
import { Product, Toast } from '@/types/index';
import api from '@/lib/adapters';

export function useExportData(
  filteredData: Product[],
  addToast: (type: Toast["type"], message: string) => void,
  t: (key: string, fallback?: string) => string
) {
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = useCallback(async (
    format: 'csv' | 'json' | 'xml' = 'csv',
    selectedColumns?: string[] // if provided, only these attributes are included
  ) => {
    setIsExporting(true);
    try {
      const dataToExport = selectedColumns && selectedColumns.length > 0 
        ? filteredData.map(product => {
            const filteredProps: Product["properties"] = {};
            selectedColumns.forEach(key => {
              if (product.properties[key]) {
                filteredProps[key] = product.properties[key];
              }
            });
            return {
              ...product,
              properties: filteredProps
            };
          })
        : filteredData;
      
      const blob = await api.exportReport(dataToExport as Product[], format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      const ext = format === 'json' ? 'json' : format === 'xml' ? 'xml' : 'csv';
      a.download = `ResinDB_Export_${new Date().toISOString().split("T")[0]}.${ext}`;
      document.body.appendChild(a);
      a.click();
      
      // Delay revocation to ensure browser has started the download
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }, 100);
      
      addToast("success", t("reportGenerated"));
    } catch (error) {
      addToast(
        "error",
        t("exportFailed") +
          (error instanceof Error ? error.message : t("unknownError")),
      );
    } finally {
      setIsExporting(false);
    }
  }, [filteredData, addToast, t]);

  return { isExporting, handleExport };
}
