import React, { forwardRef, useMemo } from "react";
import type { Product } from "@/types/index";
import { useLanguage } from "@/contexts/LanguageContext";
import {
  assessProductForScreening,
  summarizeScreening,
  type ProductScreeningResult,
  type ScreeningStatus,
  type ScreeningThresholds,
} from "@/lib/qaScreening";

interface PdfQaReportTemplateProps {
  products: Product[];
  analyst: string;
  worksheetNo: string;
  notes: string;
  thresholds?: ScreeningThresholds;
}

function statusText(status: ScreeningStatus, language: string): string {
  if (status === "ASSESSED_WITHIN_DECLARED_THRESHOLD") {
    return language === "zh" ? "已评估：处于声明阈值内" : "Assessed: within declared threshold";
  }
  if (status === "ASSESSED_OUTSIDE_DECLARED_THRESHOLD") {
    return language === "zh" ? "已评估：超出声明阈值" : "Assessed: outside declared threshold";
  }
  return language === "zh" ? "未评估" : "Not assessed";
}

function statusClass(status: ScreeningStatus): string {
  if (status === "ASSESSED_WITHIN_DECLARED_THRESHOLD") {
    return "bg-emerald-50 text-emerald-800 border-emerald-200";
  }
  if (status === "ASSESSED_OUTSIDE_DECLARED_THRESHOLD") {
    return "bg-rose-50 text-rose-800 border-rose-200";
  }
  return "bg-amber-50 text-amber-800 border-amber-200";
}

function displayValue(result: ProductScreeningResult["criteria"][number]): string {
  if (result.canonicalValue === null) return "—";
  return `${result.canonicalValue.toLocaleString("en-US", { maximumFractionDigits: 6 })} ${result.canonicalUnit}`;
}

function thresholdText(result: ProductScreeningResult["criteria"][number]): string {
  const { min, max } = result.declaredRange;
  if (min === undefined && max === undefined) return "—";
  if (min !== undefined && max !== undefined) {
    return `${min}–${max} ${result.canonicalUnit}`;
  }
  if (min !== undefined) return `≥ ${min} ${result.canonicalUnit}`;
  return `≤ ${max} ${result.canonicalUnit}`;
}

export const PdfQaReportTemplate = forwardRef<HTMLDivElement, PdfQaReportTemplateProps>(
  ({ products, analyst, worksheetNo, notes, thresholds }, ref) => {
    const { language } = useLanguage();
    const results = useMemo(
      () => products.map((product) => assessProductForScreening(product, thresholds)),
      [products, thresholds],
    );
    const summary = useMemo(() => summarizeScreening(results), [results]);
    const generatedDate = new Date().toLocaleDateString(language === "zh" ? "zh-CN" : "en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });

    return (
      <div style={{ position: "absolute", top: "-9999px", left: "-9999px" }}>
        <div
          ref={ref}
          style={{ width: "850px", backgroundColor: "#ffffff", color: "#0f172a" }}
          className="p-10 font-sans"
        >
          <header className="border-b-2 border-slate-900 pb-5">
            <div className="flex items-start justify-between gap-8">
              <div>
                <div className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">
                  ResinDB · declared-data analysis
                </div>
                <h1 className="mt-2 text-2xl font-black tracking-tight text-slate-950">
                  {language === "zh" ? "数据质量与阈值筛查工作表" : "Data Quality / Screening Worksheet"}
                </h1>
                <p className="mt-2 max-w-2xl text-xs leading-5 text-slate-600">
                  {language === "zh"
                    ? "仅比较当前记录中的声明数据与本工作表阈值。缺失、非有限、单位不兼容或条件不完整的数据保持“未评估”。"
                    : "This worksheet only compares declared data with the thresholds shown below. Missing, non-finite, unit-incompatible, or condition-incomplete data remain not assessed."}
                </p>
              </div>
              <div className="min-w-48 text-right text-[10px] leading-5 text-slate-600">
                <div><span className="font-bold">{language === "zh" ? "工作表编号" : "Worksheet"}:</span> {worksheetNo}</div>
                <div><span className="font-bold">{language === "zh" ? "生成日期" : "Generated"}:</span> {generatedDate}</div>
                <div><span className="font-bold">{language === "zh" ? "分析人员" : "Analyst"}:</span> {analyst || "—"}</div>
              </div>
            </div>
          </header>

          <section className="mt-5 grid grid-cols-4 gap-3">
            {[
              [language === "zh" ? "记录总数" : "Records", summary.totalProducts],
              [language === "zh" ? "阈值内" : "Within", summary.within],
              [language === "zh" ? "阈值外" : "Outside", summary.outside],
              [language === "zh" ? "未评估" : "Not assessed", summary.notAssessed],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="text-[9px] font-bold uppercase tracking-wider text-slate-500">{label}</div>
                <div className="mt-1 text-xl font-black tabular-nums text-slate-900">{value}</div>
              </div>
            ))}
          </section>

          <section className="mt-5 rounded-lg border border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-700">
                {language === "zh" ? "声明阈值" : "Declared thresholds"}
              </h2>
              <span className={`rounded border px-2 py-1 text-[9px] font-bold ${statusClass(summary.status)}`}>
                {statusText(summary.status, language)}
              </span>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-3 text-[10px]">
              <div className="rounded bg-slate-50 p-2">MFR min: <strong>{thresholds ? `${thresholds.mfrMin} g/10 min` : "—"}</strong></div>
              <div className="rounded bg-slate-50 p-2">MFR max: <strong>{thresholds ? `${thresholds.mfrMax} g/10 min` : "—"}</strong></div>
              <div className="rounded bg-slate-50 p-2">Tensile min: <strong>{thresholds ? `${thresholds.tensileMinMpa} MPa` : "—"}</strong></div>
            </div>
          </section>

          <section className="mt-5 space-y-4">
            {results.map((result) => (
              <article key={result.productId} className="overflow-hidden rounded-lg border border-slate-200">
                <div className="flex items-center justify-between bg-slate-900 px-4 py-2 text-white">
                  <div>
                    <span className="text-xs font-black">{result.gradeName}</span>
                    <span className="ml-2 text-[9px] text-slate-300">ID: {result.productId}</span>
                  </div>
                  <span className="text-[9px] font-bold">{statusText(result.status, language)}</span>
                </div>
                <table className="w-full table-fixed border-collapse text-[9px]">
                  <thead className="bg-slate-100 text-left text-slate-600">
                    <tr>
                      <th className="w-[17%] px-3 py-2">{language === "zh" ? "筛查项" : "Criterion"}</th>
                      <th className="w-[20%] px-3 py-2">{language === "zh" ? "识别字段" : "Resolved field"}</th>
                      <th className="w-[17%] px-3 py-2">{language === "zh" ? "规范值" : "Canonical value"}</th>
                      <th className="w-[17%] px-3 py-2">{language === "zh" ? "声明阈值" : "Threshold"}</th>
                      <th className="w-[29%] px-3 py-2">{language === "zh" ? "状态 / 原因" : "Status / reasons"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.criteria.map((criterion) => (
                      <tr key={criterion.criterion} className="border-t border-slate-200 align-top">
                        <td className="px-3 py-2 font-bold">{criterion.criterion}</td>
                        <td className="break-words px-3 py-2">{criterion.rawPropertyName ?? "—"}</td>
                        <td className="px-3 py-2 font-mono">{displayValue(criterion)}</td>
                        <td className="px-3 py-2 font-mono">{thresholdText(criterion)}</td>
                        <td className="px-3 py-2">
                          <div>{statusText(criterion.status, language)}</div>
                          {criterion.reasonCodes.length > 0 && (
                            <div className="mt-1 break-words font-mono text-[8px] text-slate-500">
                              {criterion.reasonCodes.join(", ")}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </article>
            ))}
          </section>

          <section className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4 text-[10px] leading-5 text-slate-700">
            <div className="font-black uppercase tracking-wider text-slate-800">
              {language === "zh" ? "边界说明" : "Boundary statement"}
            </div>
            <p className="mt-1">
              {language === "zh"
                ? "本工作表仅用于内部数据筛查，不作材料放行或法规判断。字段、方法、条件、来源和证据范围应由授权人员另行核验。"
                : "For internal data screening only. No material-release or regulatory decision is made. Fields, methods, conditions, sources, and evidence scope require separate review by authorized personnel."}
            </p>
            {notes.trim() && <p className="mt-2"><strong>{language === "zh" ? "备注" : "Notes"}:</strong> {notes}</p>}
          </section>

          <footer className="mt-5 border-t border-slate-200 pt-3 text-center text-[8px] uppercase tracking-widest text-slate-400">
            {language === "zh" ? "系统生成的数据筛查工作表" : "System-generated data-screening worksheet"}
          </footer>
        </div>
      </div>
    );
  },
);

PdfQaReportTemplate.displayName = "PdfQaReportTemplate";
