import React, { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, Bookmark, Download, FileText, Loader2, User, X } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { useToasts } from "@/contexts/ToastContext";
import { useAuth } from "@/contexts/AuthContext";
import type { Product } from "@/types/index";
import { PdfQaReportTemplate } from "@/components/features/Export/PdfQaReportTemplate";
import type { ScreeningThresholds } from "@/lib/qaScreening";

interface QaReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  products: Product[];
}

function parseFiniteInput(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed || !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/u.test(trimmed)) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

export const QaReportModal: React.FC<QaReportModalProps> = ({ isOpen, onClose, products }) => {
  const { language } = useLanguage();
  const { addToast } = useToasts();
  const { currentUser } = useAuth();
  const [analyst, setAnalyst] = useState(currentUser?.name || currentUser?.email || "");
  const [worksheetNo, setWorksheetNo] = useState("SCREEN-PENDING");
  const [notes, setNotes] = useState("");
  const [mfrMinInput, setMfrMinInput] = useState("0.8");
  const [mfrMaxInput, setMfrMaxInput] = useState("25");
  const [tensileMinInput, setTensileMinInput] = useState("20");
  const [isGenerating, setIsGenerating] = useState(false);
  const pdfRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isOpen) setWorksheetNo(`SCREEN-${Date.now().toString().slice(-8)}`);
  }, [isOpen]);

  const t = (zh: string, en: string) => (language === "zh" ? zh : en);
  const thresholds = useMemo<ScreeningThresholds | undefined>(() => {
    const mfrMin = parseFiniteInput(mfrMinInput);
    const mfrMax = parseFiniteInput(mfrMaxInput);
    const tensileMinMpa = parseFiniteInput(tensileMinInput);
    if (mfrMin === null || mfrMax === null || tensileMinMpa === null || mfrMin > mfrMax) {
      return undefined;
    }
    return { mfrMin, mfrMax, tensileMinMpa };
  }, [mfrMinInput, mfrMaxInput, tensileMinInput]);

  const handleExportPdf = async () => {
    if (!pdfRef.current || products.length === 0) return;
    setIsGenerating(true);
    addToast("info", t("正在生成数据筛查工作表…", "Generating data-screening worksheet…"));
    try {
      const [html2canvasModule, jsPdfModule] = await Promise.all([
        import("html2canvas"),
        import("jspdf"),
      ]);
      const canvas = await html2canvasModule.default(pdfRef.current, {
        scale: 2,
        useCORS: true,
        allowTaint: false,
        backgroundColor: "#ffffff",
      });
      const pdf = new jsPdfModule.jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      const width = pdf.internal.pageSize.getWidth();
      const height = (canvas.height * width) / canvas.width;
      pdf.addImage(canvas.toDataURL("image/png"), "PNG", 0, 0, width, height);
      pdf.save(`ResinDB_Data_Screening_${worksheetNo}.pdf`);
      addToast("success", t("数据筛查工作表已导出。", "Data-screening worksheet exported."));
    } catch (error) {
      console.error(error);
      addToast("error", t("PDF 生成失败。", "PDF generation failed."));
    } finally {
      setIsGenerating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[150] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-[150] bg-slate-950/40 backdrop-blur-md"
        />
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 12 }}
          className="relative z-[160] flex max-h-[88vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950"
        >
          <header className="flex items-center justify-between border-b border-slate-200 px-6 py-5 dark:border-slate-800">
            <div className="flex items-center gap-3">
              <span className="rounded-xl bg-indigo-50 p-2.5 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400">
                <FileText size={20} />
              </span>
              <div>
                <h2 className="text-base font-black text-slate-900 dark:text-white">
                  {t("数据质量与阈值筛查工作表", "Data Quality / Screening Worksheet")}
                </h2>
                <p className="mt-0.5 text-xs text-slate-500">
                  {t("比较声明数据与用户输入阈值；未知数据不作零值处理。", "Compare declared data with user-entered thresholds; unknown data never becomes zero.")}
                </p>
              </div>
            </div>
            <button onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900" aria-label={t("关闭", "Close")}>
              <X size={18} />
            </button>
          </header>

          <div className="overflow-y-auto p-6">
            <div className="mb-6 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <p>{t("该输出仅供内部数据筛查，不作材料放行或法规判断。缺失单位、MFR 温度/负荷、非有限值或无法识别的字段均保持“未评估”。", "This output is for internal data screening only. It makes no material-release or regulatory decision. Missing units, MFR temperature/load, non-finite values, and unresolved fields remain not assessed.")}</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <section className="space-y-4">
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-500">{t("工作表元信息", "Worksheet metadata")}</h3>
                <label className="block text-xs font-bold text-slate-600 dark:text-slate-300">
                  {t("分析人员", "Analyst")}
                  <div className="relative mt-1.5">
                    <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input value={analyst} onChange={(event: React.ChangeEvent<HTMLInputElement>) => setAnalyst(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-xs outline-none focus:border-indigo-500 dark:border-slate-800 dark:bg-slate-900" />
                  </div>
                </label>
                <label className="block text-xs font-bold text-slate-600 dark:text-slate-300">
                  {t("工作表编号", "Worksheet number")}
                  <div className="relative mt-1.5">
                    <Bookmark size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input value={worksheetNo} onChange={(event: React.ChangeEvent<HTMLInputElement>) => setWorksheetNo(event.target.value)} className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 font-mono text-xs outline-none focus:border-indigo-500 dark:border-slate-800 dark:bg-slate-900" />
                  </div>
                </label>
                <label className="block text-xs font-bold text-slate-600 dark:text-slate-300">
                  {t("备注", "Notes")}
                  <textarea value={notes} onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => setNotes(event.target.value)} rows={4} className="mt-1.5 w-full resize-none rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs outline-none focus:border-indigo-500 dark:border-slate-800 dark:bg-slate-900" />
                </label>
              </section>

              <section className="space-y-4">
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-500">{t("声明阈值", "Declared thresholds")}</h3>
                {[
                  [t("MFR 最小值 (g/10 min)", "MFR minimum (g/10 min)"), mfrMinInput, setMfrMinInput],
                  [t("MFR 最大值 (g/10 min)", "MFR maximum (g/10 min)"), mfrMaxInput, setMfrMaxInput],
                  [t("拉伸强度最小值 (MPa)", "Tensile minimum (MPa)"), tensileMinInput, setTensileMinInput],
                ].map(([label, value, setter]) => (
                  <label key={String(label)} className="block text-xs font-bold text-slate-600 dark:text-slate-300">
                    {String(label)}
                    <input
                      type="text"
                      inputMode="decimal"
                      value={String(value)}
                      onChange={(event: React.ChangeEvent<HTMLInputElement>) => (setter as React.Dispatch<React.SetStateAction<string>>)(event.target.value)}
                      className="mt-1.5 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs outline-none focus:border-indigo-500 dark:border-slate-800 dark:bg-slate-900"
                    />
                  </label>
                ))}
                {!thresholds && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-200">
                    {t("阈值配置无效；导出内容将保持“未评估”。", "Threshold configuration is invalid; exported results will remain not assessed.")}
                  </div>
                )}
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                  {t(`已选择 ${products.length} 条材料记录。`, `${products.length} material record(s) selected.`)}
                </div>
              </section>
            </div>
          </div>

          <footer className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-6 py-4 dark:border-slate-800 dark:bg-slate-900/50">
            <span className="text-xs text-slate-500">
              {t("无外部检测与审批证据时，工作表不产生认证、法规或放行结论。", "Without external test and approval evidence, this worksheet produces no certification, regulatory, or release conclusion.")}
            </span>
            <button
              type="button"
              disabled={isGenerating || products.length === 0}
              onClick={handleExportPdf}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-black text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isGenerating ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
              {t("导出筛查工作表", "Export screening worksheet")}
            </button>
          </footer>

          <PdfQaReportTemplate
            ref={pdfRef}
            products={products}
            analyst={analyst}
            worksheetNo={worksheetNo}
            notes={notes}
            thresholds={thresholds}
          />
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
