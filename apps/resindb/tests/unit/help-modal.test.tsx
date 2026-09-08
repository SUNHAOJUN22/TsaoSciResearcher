import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HelpModal from "@/components/modals/HelpModal";
import { LanguageProvider } from "@/contexts/LanguageContext";

const renderHelp = (onClose = vi.fn()) => {
  render(
    <LanguageProvider>
      <HelpModal isOpen onClose={onClose} />
    </LanguageProvider>,
  );
  return onClose;
};

describe("HelpModal", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("shows truthful Chinese import, export and role boundaries", () => {
    window.localStorage.setItem("resindb-language", "zh");
    renderHelp();

    expect(screen.getByRole("dialog", { name: "帮助中心" })).toBeInTheDocument();
    expect(screen.getByText("支持 CSV、JSON、TXT 格式")).toBeInTheDocument();
    expect(screen.getByText("支持 CSV、JSON、XML、PDF")).toBeInTheDocument();
    expect(screen.getByText("Admin、Editor、Viewer 仅用于界面演示")).toBeInTheDocument();
    expect(screen.queryByText(/Excel|RBAC/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "关闭帮助中心" })).toBeInTheDocument();
  });

  it("renders the verified English capability boundary", () => {
    window.localStorage.setItem("resindb-language", "en");
    renderHelp();

    expect(screen.getByRole("dialog", { name: "Help center" })).toBeInTheDocument();
    expect(screen.getByText("CSV, JSON and TXT are supported")).toBeInTheDocument();
    expect(screen.getByText("CSV, JSON, XML and PDF are supported")).toBeInTheDocument();
    expect(screen.getByText("Admin, Editor and Viewer demonstrate UI behavior only")).toBeInTheDocument();
  });

  it("closes on Escape", () => {
    const onClose = renderHelp();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
