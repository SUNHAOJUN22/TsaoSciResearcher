import { useEffect, useRef } from "react";
import { ModalType } from '@/contexts/ModalContext';

interface UseShortcutsProps {
  closeAllModals: () => void;
  openModal: (modalName: ModalType) => void;
  setShowSidebar: React.Dispatch<React.SetStateAction<boolean>>;
  selectedIds: Set<string>;
  handleExport: () => void;
}

export function useShortcuts({
  closeAllModals,
  openModal,
  setShowSidebar,
  selectedIds,
  handleExport,
}: UseShortcutsProps) {
  // Use refs to avoid re-binding event listeners on every prop change
  const closeAllModalsRef = useRef(closeAllModals);
  const openModalRef = useRef(openModal);
  const selectedIdsRef = useRef(selectedIds);
  const handleExportRef = useRef(handleExport);

  useEffect(() => {
    closeAllModalsRef.current = closeAllModals;
    openModalRef.current = openModal;
    selectedIdsRef.current = selectedIds;
    handleExportRef.current = handleExport;
  }, [closeAllModals, openModal, selectedIds, handleExport]);

  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;

      if (e.key === "Escape") {
        closeAllModalsRef.current();
      }

      if (e.key === "/" && !isInput) {
        e.preventDefault();
        const searchInput = document.getElementById("global-search-input");
        searchInput?.focus();
        if (searchInput && searchInput instanceof HTMLInputElement) {
          searchInput.select();
        }
      }

      if (isInput && e.key !== "Escape") return;

      if (e.key === "?") {
        openModalRef.current("shortcuts");
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "/") {
        e.preventDefault();
        setShowSidebar((prev) => !prev);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        openModalRef.current("commandPalette");
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "i") {
        e.preventDefault();
        openModalRef.current("import");
      }
      if (
        (e.ctrlKey || e.metaKey) &&
        e.key === "e" &&
        selectedIdsRef.current.size > 0
      ) {
        e.preventDefault();
        handleExportRef.current();
      }
    };
    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, [setShowSidebar]);
}
