import React, { createContext, useContext, useState, useCallback } from "react";
import { Product } from '@/types/index';

export type ModalType =
  | "import"
  | "systemHealth"
  | "feedback"
  | "help"
  | "shortcuts"
  | "commandPalette"
  | "profile"
  | "admin"
  | "batchEdit"
  | "comparison"
  | "addProduct"
  | "smartAnalysis"
  | "databaseSync"
  | "formulaEditor"
  | "qaReport"
  | "bulkReorder"
  | "bulkTagging"
  | "dataQualityAudit"
  | "smartExport";

interface ModalContextType {
  openModals: Set<ModalType>;
  viewingProduct: Product | null;
  analyzingProduct: Product | null;
  openModal: (type: ModalType) => void;
  closeModal: (type: ModalType) => void;
  closeAllModals: () => void;
  setViewingProduct: (product: Product | null) => void;
  setAnalyzingProduct: (product: Product | null) => void;
  closeDetail: () => void;
  isModalOpen: (type: ModalType) => boolean;
}

const ModalContext = createContext<ModalContextType | undefined>(undefined);

export const ModalProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [openModals, setOpenModals] = useState<Set<ModalType>>(new Set());
  const [viewingProduct, setViewingProduct] = useState<Product | null>(null);
  const [analyzingProduct, setAnalyzingProduct] = useState<Product | null>(null);

  const openModal = useCallback((type: ModalType) => {
    setOpenModals((prev) => new Set(prev).add(type));
  }, []);

  const closeModal = useCallback((type: ModalType) => {
    setOpenModals((prev) => {
      const next = new Set(prev);
      next.delete(type);
      return next;
    });
  }, []);

  const closeAllModals = useCallback(() => {
    setOpenModals(new Set());
    setViewingProduct(null);
    setAnalyzingProduct(null);
  }, []);

  const closeDetail = useCallback(() => {
    setViewingProduct(null);
  }, []);

  const isModalOpen = useCallback(
    (type: ModalType) => openModals.has(type),
    [openModals]
  );

  return (
    <ModalContext.Provider
      value={{
        openModals,
        viewingProduct,
        analyzingProduct,
        openModal,
        closeModal,
        closeAllModals,
        setViewingProduct,
        setAnalyzingProduct,
        closeDetail,
        isModalOpen,
      }}
    >
      {children}
    </ModalContext.Provider>
  );
};

 
export const useModals = () => {
  const context = useContext(ModalContext);
  if (!context) {
    throw new Error("useModals must be used within a ModalProvider");
  }
  return context;
};
