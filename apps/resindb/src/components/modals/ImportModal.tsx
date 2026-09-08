import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import Papa from "papaparse";
import {
  X,
  FileSpreadsheet,
  UploadCloud,
  CheckCircle,
  AlertCircle,
  Database,
  Filter,
  Clipboard,
  FileText,
  FileJson,
  Image as ImageIcon,
  Trash2,
  FileDown,
  ChevronRight,
  Info,
  Settings,
  PlusCircle,
  Check,
  Search
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { Product, PropertyValue } from '@/types/index';
import { motion, AnimatePresence } from "motion/react";
import { logger } from "@/lib/logger";
import { getProductValidationWarnings } from '@/utils/productUtils';


interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport?: (products: Product[]) => void;
  allProducts?: Product[];
}

interface RawFileContent {
  fileName: string;
  headers: string[];
  rows: Record<string, unknown>[];
}

export const ImportModal: React.FC<ImportModalProps> = React.memo(({
  isOpen,
  onClose,
  onImport,
  allProducts = [],
}) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [isDragging, setIsDragging] = useState(false);
  const [stagedFiles, setStagedFiles] = useState<File[]>([]);
  const [importErrors, setImportErrors] = useState<string[]>([]);
  const [parsedProducts, setParsedProducts] = useState<Product[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { t } = useLanguage();

  // Advanced Mapping & Ingestion States
  const [rawFileContents, setRawFileContents] = useState<RawFileContent[]>([]);
  const [uniqueHeaders, setUniqueHeaders] = useState<string[]>([]);
  const [columnMappings, setColumnMappings] = useState<Record<string, string>>({});
  const [duplicateAction, setDuplicateAction] = useState<"merge" | "overwrite" | "skip" | "duplicate">("merge");
  
  // Import method switch tab
  const [importSourceTab, setImportSourceTab] = useState<"file" | "clipboard">("file");
  const [rawClipboardText, setRawClipboardText] = useState("");
  
  // Sandbox query & inline cell editing states
  const [sandboxSearch, setSandboxSearch] = useState("");
  const [editingCell, setEditingCell] = useState<{ id: string; field: "gradeName" | "manufacturer" | string } | null>(null);

  // Memoized duplicate count for live reactiveness
  const computedDuplicateOverlapCount = useMemo(() => {
    return parsedProducts.filter((p) =>
      (allProducts || []).some((x) => x.gradeName.trim().toUpperCase() === p.gradeName.trim().toUpperCase())
    ).length;
  }, [parsedProducts, allProducts]);
  

  // Custom properties added during mapping process
  const [customColumns, setCustomColumns] = useState<string[]>([]);
  const [newCustomColumnName, setNewCustomColumnName] = useState("");
  const [showCustomColumnInput, setShowCustomColumnInput] = useState(false);

  // Lab Experimental Settings
  const [isExperimentalImport, setIsExperimentalImport] = useState<boolean>(false);
  const [experimentalLabName, setExperimentalLabName] = useState<string>("");

  // States for fast manual entry of real lab stress testing measurement results
  const [manualGradeName, setManualGradeName] = useState<string>("自测HDPE-Exp1");
  const [manualManufacturer, setManualManufacturer] = useState<string>("核心实验室自测");
  const [manualDensity, setManualDensity] = useState<string>("0.954");
  const [manualMFR, setManualMFR] = useState<string>("0.95");
  const [manualStrength, setManualStrength] = useState<string>("24.8");
  const [manualModulus, setManualModulus] = useState<string>("1180");
  const [isManualFormOpen, setIsManualFormOpen] = useState<boolean>(false);

  // Available database standard attributes for mapping dropdown
  const STANDARD_PROPERTIES = [
    { key: "gradeName", label: "牌号名称 (Grade Name) *", isRequired: true, isMeta: true },
    { key: "manufacturer", label: "生产厂家 (Manufacturer)", isMeta: true },
    { key: "密度", label: "密度 (g/cm³)", unit: "g/cm³" },
    { key: "熔体质量流动速率", label: "熔体流动速率 (MFI / MFR)", unit: "g/10min" },
    { key: "拉伸屈服应力", label: "拉伸应力 / 强度", unit: "MPa" },
    { key: "弯曲模量", label: "弯曲模量 (Flexural Modulus)", unit: "MPa" },
    { key: "悬臂梁缺口冲击强度", label: "悬臂冲击强度 (Izod Impact)", unit: "kJ/m²" },
    { key: "断裂伸长率", label: "断裂伸长率 (Elongation)", unit: "%" },
    { key: "洛氏硬度", label: "洛氏硬度 (Rockwell Hardness)", unit: "R" },
    { key: "热变形温度", label: "热变形温度 (HDT)", unit: "°C" },
    { key: "成型收缩率", label: "成型收缩率 (Shrinkage)", unit: "%" },
    { key: "灰分", label: "灰分含量 (Ash Content)", unit: "%" }
  ];

  const handleSaveManualRecord = () => {
    if (!manualGradeName.trim()) {
      return;
    }
    const now = new Date().toISOString().split("T")[0];
    const newProduct: Product = {
      id: `manual-lab-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
      gradeName: manualGradeName.trim(),
      manufacturer: manualManufacturer.trim() || t("experimentalLab", "自测实验室"),
      manufacturerId: "m-exp-lab",
      categoryIds: ["root_plastic"],
      createdAt: now,
      updatedAt: now,
      isExperimental: true,
      properties: {},
    };

    if (manualDensity.trim() && !isNaN(parseFloat(manualDensity))) {
      newProduct.properties["密度"] = { value: parseFloat(manualDensity), unit: "g/cm³" };
    }
    if (manualMFR.trim() && !isNaN(parseFloat(manualMFR))) {
      newProduct.properties["熔体质量流动速率"] = { value: parseFloat(manualMFR), unit: "g/10min" };
    }
    if (manualStrength.trim() && !isNaN(parseFloat(manualStrength))) {
      newProduct.properties["拉伸屈服应力"] = { value: parseFloat(manualStrength), unit: "MPa" };
    }
    if (manualModulus.trim() && !isNaN(parseFloat(manualModulus))) {
      newProduct.properties["弯曲模量"] = { value: parseFloat(manualModulus), unit: "MPa" };
    }

    setParsedProducts([newProduct]);
    setStep(4);
  };

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setTimeout(() => {
        setStep(1);
        setStagedFiles([]);
        setImportErrors([]);
        setParsedProducts([]);
        setIsExperimentalImport(false);
        setExperimentalLabName("");
        setRawFileContents([]);
        setUniqueHeaders([]);
        setColumnMappings({});
        setDuplicateAction("merge");
        setCustomColumns([]);
        setRawClipboardText("");
        setSandboxSearch("");
        setEditingCell(null);
      }, 300);
    }
  }, [isOpen]);

  /**
   * Helper to perform fuzzy guessing of column names to target attributes
   */
  const guessColumnMappings = (headers: string[]): Record<string, string> => {
    const mappings: Record<string, string> = {};
    headers.forEach((header) => {
      const lower = header.toLowerCase().trim();
      if (
        lower.includes("grade") || 
        lower.includes("牌号") || 
        lower === "name" || 
        lower.includes("名称") || 
        lower.includes("型号")
      ) {
        mappings[header] = "gradeName";
      } else if (
        lower.includes("manufacturer") || 
        lower.includes("厂家") || 
        lower.includes("company") || 
        lower.includes("生产商") || 
        lower.includes("单位") ||
        lower.includes("品牌") ||
        lower.includes("商标")
      ) {
        mappings[header] = "manufacturer";
      } else if (lower.includes("density") || lower.includes("密度") || lower.includes("比重")) {
        mappings[header] = "密度";
      } else if (
        lower.includes("mfr") || 
        lower.includes("mfi") || 
        lower.includes("熔融指数") || 
        lower.includes("流动速率") ||
        lower.includes("熔体质量")
      ) {
        mappings[header] = "熔体质量流动速率";
      } else if (
        lower.includes("tensile") || 
        lower.includes("拉伸强度") || 
        lower.includes("拉伸屈服") || 
        lower.includes("抗拉强度")
      ) {
        mappings[header] = "拉伸屈服应力";
      } else if (
        lower.includes("modulus") || 
        lower.includes("弯曲模量") || 
        lower.includes("挠曲模量") || 
        lower.includes("刚性模量")
      ) {
        mappings[header] = "弯曲模量";
      } else if (
        lower.includes("impact") || 
        lower.includes("缺口冲击") || 
        lower.includes("悬臂梁") || 
        lower.includes("izod")
      ) {
        mappings[header] = "悬臂梁缺口冲击强度";
      } else if (lower.includes("elongation") || lower.includes("断裂伸长率") || lower.includes("伸长率")) {
        mappings[header] = "断裂伸长率";
      } else if (lower.includes("hardness") || lower.includes("硬度") || lower.includes("rockwell")) {
        mappings[header] = "洛氏硬度";
      } else if (lower.includes("hdt") || lower.includes("热变形") || lower.includes("变形温度")) {
        mappings[header] = "热变形温度";
      } else if (lower.includes("shrinkage") || lower.includes("收缩率") || lower.includes("成型收缩")) {
        mappings[header] = "成型收缩率";
      } else if (lower.includes("ash") || lower.includes("灰分")) {
        mappings[header] = "灰分";
      } else {
        mappings[header] = "[skip]"; // Default to ignore unless matches are clear
      }
    });
    return mappings;
  };

  /**
   * Universal Raw File Parser (CSV, JSON, TXT)
   * Populates the RawFileContent interface for Step 2 schema mapping
   */
  const parseRawFile = async (file: File, onProgress: (progress: number) => void): Promise<RawFileContent> => {
    return new Promise((resolve, reject) => {
        const isJson = file.name.endsWith(".json");

      if (isJson) {
        const reader = new FileReader();
        reader.onload = (e) => {
          try {
            const result = e.target?.result as string;
            const data = JSON.parse(result);
            let rows: Record<string, unknown>[] = [];
            if (Array.isArray(data)) {
              rows = data as Record<string, unknown>[];
            } else if (data && typeof data === "object" && "products" in data && Array.isArray((data as Record<string, unknown>).products)) {
              rows = (data as Record<string, unknown>).products as Record<string, unknown>[];
            } else if (data && typeof data === "object") {
              rows = [data as Record<string, unknown>];
            }

            const keysSet = new Set<string>();
            rows.forEach((r) => Object.keys(r).forEach((k) => keysSet.add(k)));
            onProgress(100);
            resolve({
              fileName: file.name,
              headers: Array.from(keysSet),
              rows,
            });
          } catch {
            reject(new Error("JSON 格式错误，请检查结构。"));
          }
        };
        reader.readAsText(file);
      } else {
        // Standard CSV/TXT Papa parse
        Papa.parse(file, {
          header: true,
          skipEmptyLines: true,
          complete: (results) => {
            const rows = results.data as Record<string, unknown>[];
            const headers = results.meta.fields || [];
            if (headers.length === 0 && rows.length > 0) {
              const keysSet = new Set<string>();
              rows.forEach((r) => Object.keys(r).forEach((k) => keysSet.add(k)));
              headers.push(...Array.from(keysSet));
            }
            onProgress(100);
            resolve({
              fileName: file.name,
              headers,
              rows,
            });
          },
          error: (error) => {
            reject(new Error(error.message));
          },
        });
      }
    });
  };

  const [importProgress, setImportProgress] = useState(0);

  /**
   * Parses clipboard text copied directly from an Excel spreadsheet or grid structure
   */
  const parseClipboardData = () => {
    if (!rawClipboardText.trim()) return;
    
    try {
      const results = Papa.parse(rawClipboardText.trim(), {
        header: true,
        skipEmptyLines: true,
      });
      
      if (results.data.length === 0) {
        setImportErrors(["无法从剪贴板解析任何含有表头的行。请确保包含列标题并且使用制表符（Tab）或逗号分隔字段。"]);
        return;
      }
      
      const headers = results.meta.fields || [];
      const dataRows = results.data as Record<string, unknown>[];
      if (headers.length === 0 && dataRows.length > 0) {
        const keysSet = new Set<string>();
        dataRows.forEach((r) => Object.keys(r).forEach((k) => keysSet.add(k)));
        headers.push(...Array.from(keysSet));
      }
      
      setRawFileContents([{
        fileName: "剪贴板直接粘滞数据 (Clipboard Data)",
        headers,
        rows: dataRows,
      }]);
      
      // Auto guess mappings for pasted text
      setUniqueHeaders(headers);
      const initialMappings = guessColumnMappings(headers);
      setColumnMappings(initialMappings);
      
      // Move directly to Step 2 column mappings
      setStep(2);
      setImportErrors([]);
    } catch (err) {
      setImportErrors([`剪贴板内容解析异常: ${err instanceof Error ? err.message : String(err)}`]);
    }
  };

  /**
   * Triggers the raw extraction and automatic synonyms guessing, moving to step 2 columns mapper
   */
  const processFilesToMapping = async () => {
    setStep(2);
    setImportErrors([]);
    setImportProgress(20);
    const rawContents: RawFileContent[] = [];
    const errors: string[] = [];

    const totalFiles = stagedFiles.length;
    let completedFiles = 0;

    for (const file of stagedFiles) {
      try {
        const parsedData = await parseRawFile(file, (prog) => {
          const overallProgress = Math.floor(
            (completedFiles / totalFiles) * 60 + (prog / totalFiles) * 0.4
          );
          setImportProgress(overallProgress);
        });

        if (parsedData.rows.length === 0) {
          errors.push(`文件 ${file.name} 中没有容纳任何可用记录。`);
        } else {
          rawContents.push(parsedData);
        }
        completedFiles++;
      } catch (e: unknown) {
        logger.error("Raw parsing error", e);
        errors.push(
          `文件 ${file.name} 预读取失败: ${e instanceof Error ? e.message : String(e)}`
        );
      }
    }

    if (errors.length > 0) {
      setImportErrors(errors);
      setStep(1);
      return;
    }

    setRawFileContents(rawContents);

    // Aggregate unique columns from files
    const allHeadersSet = new Set<string>();
    rawContents.forEach((f) => f.headers.forEach((h) => allHeadersSet.add(h)));
    const aggregatedHeaders = Array.from(allHeadersSet);
    setUniqueHeaders(aggregatedHeaders);

    // Initial Guessing of mapping bindings
    const initialMappings = guessColumnMappings(aggregatedHeaders);
    setColumnMappings(initialMappings);

    setImportProgress(100);
  };

  /**
   * Runs properties extraction of each row using binding states, resolving name duplicates
   */
  const generateImportProducts = () => {
    const products: Product[] = [];
    const now = new Date().toISOString().split("T")[0];
    let _duplicationDetected = 0;

    // Retrieve file column headers that represent metadata or particular keys
    const getFileHeaderFor = (target: string): string | undefined => {
      return Object.keys(columnMappings).find((h) => columnMappings[h] === target);
    };

    rawFileContents.forEach((fileContent) => {
      fileContent.rows.forEach((row) => {
        // Extract Product Identity Attributes
        const gradeHeader = getFileHeaderFor("gradeName");
        const rawGrade = gradeHeader ? row[gradeHeader] : undefined;
        if (rawGrade === undefined || String(rawGrade).trim() === "") return;

        const gradeName = String(rawGrade).trim();
        const manHeader = getFileHeaderFor("manufacturer");
        const rawMan = manHeader ? row[manHeader] : undefined;

        const manufacturer = isExperimentalImport
          ? (experimentalLabName.trim() || "自测实验室")
          : rawMan
          ? String(rawMan).trim()
          : "Imported";

        const properties: Record<string, PropertyValue> = {};

        // Extract Material Properties Attributes matching mapped rows
        Object.keys(columnMappings).forEach((header) => {
          const bindingDestination = columnMappings[header];
          if (
            bindingDestination === "[skip]" || 
            bindingDestination === "gradeName" || 
            bindingDestination === "manufacturer"
          ) {
            return;
          }

          const rawVal = row[header];
          if (rawVal === "" || rawVal === null || rawVal === undefined) return;
          const strVal = String(rawVal).trim().toUpperCase();
          if (strVal === "-" || strVal === "N/A" || strVal === "ND" || strVal === "NULL" || strVal === "NONE") return;

          // Attempt to scan standard metrics unit
          let detectedUnit = "";
          const unitMatch = header.match(/\((.*?)\)/) || header.match(/\[(.*?)\]/);
          if (unitMatch) {
            detectedUnit = unitMatch[1];
          } else {
            const matchInProps = STANDARD_PROPERTIES.find((p) => p.key === bindingDestination);
            if (matchInProps && matchInProps.unit) {
              detectedUnit = matchInProps.unit;
            }
          }

          const parseFloatValue = parseFloat(String(rawVal));
          properties[bindingDestination] = {
            value: isNaN(parseFloatValue) ? String(rawVal) : parseFloatValue,
            unit: detectedUnit,
          };
        });

        // Resolve Collision check with existing list
        const duplicatesInDB = (allProducts || []).find(
          (p) => p.gradeName.trim().toUpperCase() === gradeName.toUpperCase()
        );

        if (duplicatesInDB) {
          _duplicationDetected++;
          if (duplicateAction === "skip") {
            return; // Ignore this record fully
          } else if (duplicateAction === "overwrite") {
            products.push({
              id: duplicatesInDB.id,
              gradeName,
              manufacturer,
              manufacturerId: isExperimentalImport ? "m-exp-lab" : duplicatesInDB.manufacturerId || "m-import",
              categoryIds: duplicatesInDB.categoryIds || ["root_plastic"],
              createdAt: duplicatesInDB.createdAt || now,
              updatedAt: now,
              properties,
              isExperimental: isExperimentalImport ? true : duplicatesInDB.isExperimental,
            });
            return;
          } else if (duplicateAction === "merge") {
            const mergedProps = { ...duplicatesInDB.properties, ...properties };
            products.push({
              id: duplicatesInDB.id,
              gradeName,
              manufacturer,
              manufacturerId: isExperimentalImport ? "m-exp-lab" : duplicatesInDB.manufacturerId || "m-import",
              categoryIds: duplicatesInDB.categoryIds || ["root_plastic"],
              createdAt: duplicatesInDB.createdAt || now,
              updatedAt: now,
              properties: mergedProps,
              isExperimental: isExperimentalImport ? true : duplicatesInDB.isExperimental,
            });
            return;
          }
        }

        // Fresh record creation
        products.push({
          id: `imported-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`,
          gradeName,
          manufacturer,
          manufacturerId: isExperimentalImport ? "m-exp-lab" : "m-import",
          categoryIds: ["root_plastic"],
          createdAt: now,
          updatedAt: now,
          properties,
          isExperimental: isExperimentalImport ? true : undefined,
        });
      });
    });

    setParsedProducts(products);
    setStep(3); // Enter verification sandbox table
  };

  /**
   * Inline editor updates inside Step 3 Verification Sandbox Table
   */
  const handleUpdateParsedProduct = useCallback(
    function updateParsedProduct<K extends keyof Product>(
      id: string,
      updatedField: K,
      value: Product[K],
    ) {
      setParsedProducts((prev) =>
        prev.map((product) => (
          product.id === id ? { ...product, [updatedField]: value } : product
        )),
      );
    },
    [],
  );

  const handleUpdateParsedProperty = useCallback((id: string, propKey: string, valStr: string) => {
    setParsedProducts((prev) =>
      prev.map((p) => {
        if (p.id === id) {
          const properties = { ...p.properties };
          if (valStr.trim() === "") {
            delete properties[propKey];
          } else {
            const parsedVal = parseFloat(valStr);
            properties[propKey] = {
              ...properties[propKey],
              value: isNaN(parsedVal) ? valStr : parsedVal,
            };
          }
          return { ...p, properties };
        }
        return p;
      })
    );
  }, []);

  const handleRemoveSandboxProduct = useCallback((id: string) => {
    setParsedProducts((prev) => prev.filter((p) => p.id !== id));
  }, []);

  /**
   * Adds custom variable headers created by the user instantly to options
   */
  const handleAddCustomColumn = () => {
    if (!newCustomColumnName.trim()) return;
    const key = newCustomColumnName.trim();
    if (!customColumns.includes(key)) {
      setCustomColumns((prev) => [...prev, key]);
    }
    setNewCustomColumnName("");
    setShowCustomColumnInput(false);
  };

  const addFiles = useCallback((files: FileList | File[]) => {
    const newFiles = Array.from(files);
    setStagedFiles((prev) => [...prev, ...newFiles]);
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    const handlePaste = (e: ClipboardEvent) => {
      e.preventDefault();
      const items = e.clipboardData?.items;
      if (!items) return;
      const newFiles: File[] = [];
      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === "file") {
          const file = items[i].getAsFile();
          if (file) newFiles.push(file);
        }
      }
      if (newFiles.length > 0) addFiles(newFiles);
    };
    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, [isOpen, addFiles]);

  const removeFile = (index: number) => {
    setStagedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const getFileIcon = (file: File) => {
    if (file.type.includes("image"))
      return <ImageIcon size={18} className="text-purple-500" />;
    if (file.type.includes("json"))
      return <FileJson size={18} className="text-amber-500" />;
    if (file.name.includes("csv"))
      return <FileSpreadsheet size={18} className="text-emerald-500" />;
    return <FileText size={18} className="text-blue-500" />;
  };

  const handleDownloadTemplate = () => {
    const csvContent =
      "Grade Name,Manufacturer,Density (g/cm³),MFR (g/10min),Tensile Strength (MPa),Flexural Modulus (MPa),Impact Strength (kJ/m²)\nHDPE-Demo,Sinopec,0.954,0.95,24.8,1180,8.5\nPP-Test,LyondellBasell,0.905,12.5,32.0,1450,6.2\nABS-Sample,Chimei,1.04,22.0,45.0,2300,21.0";
    const blob = new Blob(["\uFEFF" + csvContent], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "resindb_template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="import-modal-root"
          className="fixed inset-0 z-[110] flex items-center justify-center p-4"
        >
          {/* Backdrop blurring */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          ></motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.4, bounce: 0 }}
            className="relative w-full max-w-2xl bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-705 flex flex-col max-h-[92vh] shadow-2xl rounded-2xl md:rounded-[2.2rem] overflow-hidden"
          >
            {/* Header branding */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-300 dark:border-slate-700 bg-slate-900 dark:bg-slate-950 relative overflow-hidden shrink-0">
              <div className="flex items-center gap-4 relative z-10">
                <div className="p-2.5 bg-primary-600 text-white border border-primary-700 rounded-xl shadow-inner">
                  <Database size={20} />
                </div>
                <div className="min-w-0 flex-1">
                  <h3
                    className="text-sm font-serif font-bold text-white leading-none tracking-tight mb-1 truncate"
                  >
                    {t("importTitle", "高效结构化数据导入 / Unified Ingestion")}
                  </h3>
                  <p
                    className="text-[10px] text-slate-400 font-mono uppercase tracking-widest truncate"
                  >
                    {t("dataIngestion", "POLYMER MATERIAL DATABASE INGESTION SYSTEM")}
                  </p>
                </div>
              </div>
              <motion.button
                whileHover={{
                  scale: 1.1,
                  backgroundColor: "rgba(225, 29, 72, 1)",
                }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="p-2 bg-white/10 backdrop-blur-md border border-white/20 text-white transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 z-10 rounded-xl cursor-pointer"
              >
                <X size={16} />
              </motion.button>
            </div>

            {/* Stepper Status Indicators */}
            <div className="px-6 py-3 bg-slate-50 dark:bg-slate-900 border-b border-slate-300 dark:border-slate-700 flex items-center justify-between shrink-0">
              {[
                { s: 1, name: "上传源文件" },
                { s: 2, name: "表结构映射" },
                { s: 3, name: "校验沙盒" },
                { s: 4, name: "合流完毕" }
              ].map(({ s, name }) => (
                <div key={s} className="flex items-center gap-2">
                  <div
                    className={`flex items-center justify-center w-6 h-6 font-mono font-bold text-[9px] rounded-full transition-all duration-300 border ${
                      step === s 
                        ? "bg-primary-600 text-white border-primary-600 shadow animate-pulse scale-105" 
                        : step > s 
                        ? "bg-emerald-600 text-white border-emerald-600" 
                        : "bg-white dark:bg-slate-950 text-slate-400 border-slate-300 dark:border-slate-700"
                    }`}
                  >
                    {step > s ? <Check size={10} /> : s}
                  </div>
                  <span className={`text-[10px] font-bold ${step === s ? "text-primary-600 dark:text-primary-400" : "text-slate-400 dark:text-slate-550"} hidden sm:inline`}>
                    {name}
                  </span>
                  {s < 4 && <ChevronRight size={12} className="text-slate-300 hidden sm:inline" />}
                </div>
              ))}
            </div>

            {/* Body Content of Modal */}
            <div className="p-6 overflow-y-auto custom-scrollbar flex-1 bg-white dark:bg-slate-950">
              {step === 1 && (
                <div className="space-y-6">
                  {importErrors.length > 0 && (
                    <div className="p-4 bg-rose-50 dark:bg-rose-900/20 border border-rose-205 dark:border-rose-800 rounded-xl space-y-2">
                      <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 font-mono font-bold text-[10px] uppercase tracking-widest">
                        <AlertCircle size={14} />
                        <span>检测到以下数据异常:</span>
                      </div>
                      <ul className="text-[10px] font-mono text-rose-500 dark:text-rose-450 list-disc list-inside space-y-1">
                        {importErrors.map((err, i) => (
                          <li key={i} className="truncate" title={err}>
                            {err}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Ingestion Source Switcher Tabs */}
                  <div className="flex border border-slate-200 dark:border-slate-805 p-1 bg-slate-50 dark:bg-slate-900 rounded-xl gap-1">
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.97 }}
                      type="button"
                      onClick={() => setImportSourceTab("file")}
                      className={`flex-1 py-1.5 font-serif font-bold text-xs rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                        importSourceTab === "file"
                          ? "bg-white dark:bg-slate-950 text-slate-950 dark:text-white shadow-xs border border-slate-200 dark:border-slate-800"
                          : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                      }`}
                    >
                      📁 多格式物理文件拖拉上传 (File Drop)
                    </motion.button>
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.97 }}
                      type="button"
                      onClick={() => setImportSourceTab("clipboard")}
                      className={`flex-1 py-1.5 font-serif font-bold text-xs rounded-lg transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                        importSourceTab === "clipboard"
                          ? "bg-white dark:bg-slate-950 text-slate-950 dark:text-white shadow-xs border border-slate-200 dark:border-slate-800"
                          : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                      }`}
                    >
                      📋 剪贴板 Excel 表格网格粘贴 (Clipboard Paste)
                    </motion.button>
                  </div>

                  {importSourceTab === "file" ? (
                    /* Drag-and-drop region */
                    <motion.div
                      whileHover={{ scale: 1.005 }}
                      className={`
                          relative group border-2 border-dashed p-8 md:p-10 flex flex-col items-center justify-center text-center transition-all duration-300 cursor-pointer overflow-hidden rounded-2xl
                          ${
                            isDragging
                              ? "border-primary-500 bg-primary-50 dark:bg-primary-900/10 scale-[0.99]"
                              : "border-slate-300 dark:border-slate-700 hover:border-primary-400 hover:bg-slate-50 dark:hover:bg-slate-900/40 bg-white dark:bg-slate-950 shadow-sm"
                          }
                      `}
                      onDragOver={(e) => {
                        e.preventDefault();
                        setIsDragging(true);
                      }}
                      onDragLeave={() => setIsDragging(false)}
                      onDrop={(e) => {
                        e.preventDefault();
                        setIsDragging(false);
                        addFiles(e.dataTransfer.files);
                      }}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <input
                        type="file"
                        ref={fileInputRef}
                        className="hidden"
                        multiple
                        accept=".csv,.json,.txt"
                        onChange={(e) => {
                          if (e.target.files) addFiles(e.target.files);
                        }}
                      />

                      <div
                        className={`w-14 h-14 flex items-center justify-center mb-4 transition-all duration-300 border rounded-xl ${isDragging ? "bg-primary-600 text-white border-primary-600 rotate-12 scale-110 shadow-lg" : "bg-slate-100 dark:bg-slate-900 text-slate-400 border-slate-205 dark:border-slate-800 group-hover:text-primary-500 group-hover:scale-110"}`}
                      >
                        <UploadCloud size={24} strokeWidth={1.5} />
                      </div>

                      <div className="space-y-1.5 relative z-10">
                        <h4 className="text-slate-900 dark:text-white font-serif font-bold text-sm tracking-tight">
                          {t("dragDrop", "拖拽文件到这里或")} <span className="text-primary-600 dark:text-primary-450">{t("browseFiles", "点击浏览")}</span>
                        </h4>
                        <div className="flex items-center justify-center gap-2.5 text-[10px] text-slate-400 font-mono font-bold uppercase tracking-wider">
                          <span className="flex items-center gap-1.5 px-2 py-0.5 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded">
                            <Clipboard size={10} /> Ctrl+V 粘贴
                          </span>
                          <span className="w-1 h-1 bg-slate-300 rounded-full" />
                          <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded">
                            Excel / CSV / JSON
                          </span>
                        </div>
                      </div>
                    </motion.div>
                  ) : (
                    /* Clipboard Paste Tab Content */
                    <motion.div
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-4 text-left"
                    >
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-mono font-bold text-slate-400 block uppercase tracking-wider">
                          复制 Excel 表格行列数据并直接粘贴于此 (Supports Tab/CSV Separated Grid Copying)
                        </label>
                        <textarea
                          value={rawClipboardText}
                          onChange={(e) => setRawClipboardText(e.target.value)}
                          rows={6}
                          placeholder={`例如直接从 Excel 选中复制的物性表格数据：
牌号		生产厂家		密度		熔体流动速率
HDPE-5000S	中石化		0.954		0.95
PP-M1600	中石油		0.910		1200`}
                          className="w-full px-4 py-3 font-mono text-xs border border-slate-300 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-550 rounded-xl outline-none focus:ring-1 focus:ring-primary-500 focus:bg-white dark:focus:bg-slate-950 transition-all custom-scrollbar shrink-0"
                        />
                      </div>
                      
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-[10px] font-mono text-slate-400">
                          * 粘贴数据需包含第 1 行的标题，并保证具有牌号型号列。
                        </div>
                        <div className="flex gap-2">
                          <motion.button
                            type="button"
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => setRawClipboardText(`牌号	生产厂家	密度	熔体质量流动速率	拉伸屈服应力
自测高抗冲合金-PE01	Sinopec	0.958	1.2	25.5
测试轻质PP-FR102	LyondellBasell	0.902	8.5	31.0`)}
                            className="px-3 py-1.5 border border-slate-300 dark:border-slate-750 text-slate-600 dark:text-slate-400 hover:text-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/65 flex items-center gap-1.5 transition-all text-[10px] font-mono font-bold rounded-lg cursor-pointer"
                          >
                            💡 填充自测演示网格
                          </motion.button>
                          <motion.button
                            type="button"
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={parseClipboardData}
                            disabled={!rawClipboardText.trim()}
                            className="px-4 py-1.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 disabled:opacity-40 font-mono font-bold text-[10px] uppercase tracking-widest cursor-pointer shadow-sm rounded-lg"
                          >
                            🚀 进行文本网格快速解析
                          </motion.button>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  {/* Built-in template downloader */}
                  <div className="flex flex-col sm:flex-row items-center sm:items-start gap-3 p-4 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl">
                    <div className="p-2 bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-primary-600 dark:text-primary-450 shrink-0 rounded-lg">
                      <FileDown size={16} />
                    </div>
                    <div className="flex-1 text-center sm:text-left">
                      <div className="flex flex-col sm:flex-row justify-between items-center gap-1">
                        <h4 className="text-[10px] font-mono font-bold text-slate-700 dark:text-slate-200 uppercase tracking-widest">
                          {t("downloadTemplate", "标准化物性合流数据模板 / STANDARD INGESTION TEMPLATE")}
                        </h4>
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={handleDownloadTemplate}
                          className="text-[10px] font-mono font-bold text-primary-600 hover:text-primary-700 dark:text-primary-450 hover:underline uppercase tracking-wide focus:outline-none transition-all px-2 py-0.5 rounded hover:bg-primary-50 dark:hover:bg-primary-900/20 shadow-sm"
                        >
                          Download Template .CSV
                        </motion.button>
                      </div>
                      <p className="text-[10px] font-mono text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                        {t("templateDesc", "使用规范化的密度、流动速率、拉伸和刚度标题可获得最佳自动映射体验。建议包含 '牌号(Grade)' 标识列。")}
                      </p>
                    </div>
                  </div>

                  {/* Experimental Lab Switcher */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-205 dark:border-slate-800 rounded-xl space-y-3">
                    <label className="flex items-center justify-between cursor-pointer select-none">
                      <div className="space-y-0.5">
                        <span className="text-xs font-bold text-slate-900 dark:text-slate-150 flex items-center gap-1.5">
                          🔬 标记导入产品为 [内部自测实验测量数据]
                        </span>
                        <p className="text-[10px] text-slate-400 dark:text-slate-500">
                          将激活雷达指纹偏差对比图、实验极限偏差警报和材料比对专页功能
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        checked={isExperimentalImport}
                        onChange={(e) => {
                          setIsExperimentalImport(e.target.checked);
                          if (e.target.checked && !experimentalLabName) {
                            setExperimentalLabName("自测高性能实验室");
                          }
                        }}
                        className="w-4 h-4 text-primary-600 border-slate-300 dark:border-slate-705 rounded focus:ring-primary-500 cursor-pointer"
                      />
                    </label>

                    {isExperimentalImport && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        className="space-y-1.5 pt-2 border-t border-dashed border-slate-200 dark:border-slate-700"
                      >
                        <span className="text-[9px] uppercase font-mono font-bold text-slate-400 tracking-wider block">
                          实验测试机构 / 实验室名称 (Laboratory Unit)
                        </span>
                        <input
                          type="text"
                          value={experimentalLabName}
                          onChange={(e) => setExperimentalLabName(e.target.value)}
                          placeholder="例如: 智能高分子精密物性检测中心"
                          className="w-full px-3 py-2 text-xs font-medium border border-slate-300 dark:border-slate-750 bg-white dark:bg-slate-950 text-slate-950 dark:text-white rounded-lg focus:ring-1 focus:ring-primary-500 outline-none transition-all"
                        />
                      </motion.div>
                    )}
                  </div>

                  {/* Shortcut accordion for direct key manual entry */}
                  <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-slate-50 dark:bg-slate-900/30">
                    <motion.button
                      whileHover={{ scale: 1.005 }}
                      whileTap={{ scale: 0.995 }}
                      type="button"
                      onClick={() => setIsManualFormOpen(!isManualFormOpen)}
                      className="w-full flex items-center justify-between px-4 py-3 bg-slate-100 dark:bg-slate-900/60 text-left cursor-pointer"
                    >
                      <span className="text-xs font-bold text-slate-700 dark:text-slate-250 flex items-center gap-1.5">
                        ✍️ 极速直接手动键盘录入测量数据 (无需准备多格式文件)
                      </span>
                      <span className="text-[10px] font-mono font-semibold text-primary-600 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2 py-0.5 rounded hover:bg-slate-50">
                        {isManualFormOpen ? "隐藏快速表单" : "录入单条"}
                      </span>
                    </motion.button>

                    {isManualFormOpen && (
                      <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 space-y-3 animate-in slide-in-from-top-1">
                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-1">
                            <label className="text-[10px] font-mono font-bold text-slate-400 block">自测牌号型号 *</label>
                            <input
                              type="text"
                              value={manualGradeName}
                              onChange={(e) => setManualGradeName(e.target.value)}
                              className="w-full px-3 py-1.5 text-xs font-mono border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 text-slate-900 dark:text-slate-50 rounded outline-none focus:border-primary-500"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-[10px] font-mono font-bold text-slate-400 block">测试组及单位</label>
                            <input
                              type="text"
                              value={manualManufacturer}
                              onChange={(e) => setManualManufacturer(e.target.value)}
                              className="w-full px-3 py-1.5 text-xs font-mono border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 text-slate-900 dark:text-slate-50 rounded outline-none focus:border-primary-500"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          <div className="space-y-1">
                            <label className="text-[9px] uppercase font-mono font-bold text-slate-400 block">密度 (g/cm³)</label>
                            <input
                              type="text"
                              value={manualDensity}
                              onChange={(e) => setManualDensity(e.target.value)}
                              className="w-full px-2 py-1 text-xs font-mono border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-50 bg-slate-50 dark:bg-slate-900/50 rounded"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-[9px] uppercase font-mono font-bold text-slate-400 block">熔体流动速率</label>
                            <input
                              type="text"
                              value={manualMFR}
                              onChange={(e) => setManualMFR(e.target.value)}
                              className="w-full px-2 py-1 text-xs font-mono border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-50 bg-slate-50 dark:bg-slate-900/50 rounded"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-[9px] uppercase font-mono font-bold text-slate-400 block">拉伸应力(MPa)</label>
                            <input
                              type="text"
                              value={manualStrength}
                              onChange={(e) => setManualStrength(e.target.value)}
                              className="w-full px-2 py-1 text-xs font-mono border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-50 bg-slate-50 dark:bg-slate-900/50 rounded"
                            />
                          </div>
                          <div className="space-y-1">
                            <label className="text-[9px] uppercase font-mono font-bold text-slate-400 block">弯曲模量(MPa)</label>
                            <input
                              type="text"
                              value={manualModulus}
                              onChange={(e) => setManualModulus(e.target.value)}
                              className="w-full px-2 py-1 text-xs font-mono border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-50 bg-slate-50 dark:bg-slate-900/50 rounded"
                            />
                          </div>
                        </div>

                        <div className="pt-1 flex justify-end">
                          <motion.button
                            whileHover={!manualGradeName.trim() ? {} : { scale: 1.03 }}
                            whileTap={!manualGradeName.trim() ? {} : { scale: 0.97 }}
                            type="button"
                            onClick={handleSaveManualRecord}
                            disabled={!manualGradeName.trim()}
                            className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-mono font-bold text-[9px] uppercase tracking-widest cursor-pointer shadow-sm rounded-lg"
                          >
                            🚀 生成单条并前往校验
                          </motion.button>
                        </div>
                      </div>
                    )}
                  </div>

                  {importSourceTab === "file" && stagedFiles.length > 0 && (
                    <div className="space-y-2.5 animate-in slide-in-from-bottom-2 duration-300">
                      <div className="flex items-center justify-between text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest px-1">
                        <span>已选入待解析文件 ({stagedFiles.length})</span>
                        <motion.button
                          whileHover={{ scale: 1.02, color: "#f43f5e" }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => setStagedFiles([])}
                          className="text-rose-500 hover:underline focus:outline-none transition-all cursor-pointer"
                        >
                          全部清除 (Clear All)
                        </motion.button>
                      </div>
                      <div className="max-h-44 overflow-y-auto custom-scrollbar space-y-1.5 pr-1">
                        {stagedFiles.map((file, idx) => (
                          <div
                            key={`${file.name}-${idx}`}
                            className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-705 rounded-xl hover:shadow-xs transition-shadow"
                          >
                            <div className="p-1.5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded">
                              {getFileIcon(file)}
                            </div>
                            <div className="flex-1 min-w-0 text-left">
                              <p className="text-xs font-mono font-bold text-slate-700 dark:text-slate-200 truncate">
                                {file.name}
                              </p>
                              <p className="text-[9px] text-slate-400 font-mono uppercase">
                                {formatFileSize(file.size)}
                              </p>
                            </div>
                            <motion.button
                              whileHover={{
                                scale: 1.1,
                                backgroundColor: "rgba(244, 63, 94, 0.1)",
                                color: "#f43f5e",
                              }}
                              whileTap={{ scale: 0.9 }}
                              onClick={(e) => {
                                e.stopPropagation();
                                removeFile(idx);
                              }}
                              className="p-1.5 text-slate-400 transition-all border border-slate-200 dark:border-slate-800 hover:border-rose-400 rounded-lg cursor-pointer"
                            >
                              <Trash2 size={13} />
                            </motion.button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {importSourceTab === "file" && (
                    <div className="pt-2">
                      <motion.button
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                        onClick={processFilesToMapping}
                        disabled={stagedFiles.length === 0}
                        className={`w-full py-3.5 font-mono font-bold text-[10px] uppercase tracking-widest transition-all shadow-md flex items-center justify-center gap-2 rounded-xl focus:outline-none cursor-pointer ${stagedFiles.length > 0 ? "bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-slate-100" : "bg-slate-150 dark:bg-slate-900 text-slate-400 cursor-not-allowed"}`}
                      >
                        {stagedFiles.length > 0 ? (
                          <>
                            <Database size={13} /> 开始预分析 {stagedFiles.length} 个文件
                          </>
                        ) : (
                          "请先拖入文件或点击极速录入"
                        )}
                      </motion.button>
                    </div>
                  )}
                </div>
              )}

              {/* Progress/processing step */}
              {step === 2 && uniqueHeaders.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 w-full max-w-xs mx-auto text-center">
                  <div className="relative w-12 h-12 border-2 border-slate-200 dark:border-slate-800 border-t-primary-600 animate-spin mb-6 rounded-full"></div>
                  <h4 className="text-slate-900 dark:text-slate-100 font-mono font-bold text-xs uppercase tracking-widest animate-pulse">
                    正在分析文件物理化学属性字段...
                  </h4>
                  <div className="w-full bg-slate-200 dark:bg-slate-850 h-1 rounded-full mt-4 overflow-hidden">
                    <div
                      className="bg-primary-600 h-full transition-all duration-300 animate-pulse"
                      style={{ width: `${importProgress}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Step 2 Column Mapping Interface */}
              {step === 2 && uniqueHeaders.length > 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-6"
                >
                  <div className="p-4 bg-primary-50 dark:bg-primary-950/20 border border-primary-200 dark:border-primary-850 rounded-xl flex items-start gap-3">
                    <Info size={16} className="text-primary-600 dark:text-primary-400 shrink-0 mt-0.5" />
                    <div className="space-y-1 text-left">
                      <h4 className="text-xs font-bold text-primary-800 dark:text-primary-300">
                        智能属性字段桥接与合流
                      </h4>
                      <p className="text-[10px] leading-relaxed text-primary-600 dark:text-primary-405 font-mono">
                        检测到您上传的文件中含有以下列标题，系统已通过同义模糊算法推测了其在标准高分子工艺数据库中的归属属性。您可以自由校对映射，或定义忽略某个多余段落。
                      </p>
                    </div>
                  </div>

                  {/* Schema mapping matrix */}
                  <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 rounded-xl overflow-hidden shadow-xs">
                    <div className="grid grid-cols-12 gap-2 bg-slate-50 dark:bg-slate-900 px-4 py-2 border-b border-slate-200 dark:border-slate-800 font-mono font-bold text-[9px] text-slate-500 uppercase tracking-wider text-left">
                      <div className="col-span-5">文件原始列名 / Header in File</div>
                      <div className="col-span-6">映射至数据库参数 / Mapped Parameter</div>
                      <div className="col-span-1 text-center">状态</div>
                    </div>

                    <div className="divide-y divide-slate-100 dark:divide-slate-800/60 max-h-60 overflow-y-auto custom-scrollbar">
                      {uniqueHeaders.map((header) => {
                        const destination = columnMappings[header] || "[skip]";
                        const isRequiredMatched = destination === "gradeName";
                        
                        // Extract a sample row data to preview to help user understand the content
                        let sampleVal = "";
                        if (rawFileContents[0] && rawFileContents[0].rows[0]) {
                          sampleVal = String(rawFileContents[0].rows[0][header] || "");
                          if (sampleVal.length > 25) sampleVal = sampleVal.substring(0, 22) + "...";
                        }

                        return (
                          <div key={header} className="grid grid-cols-12 gap-2 px-4 py-2.5 items-center hover:bg-slate-50/50 dark:hover:bg-slate-900/30 transition-colors text-left">
                            <div className="col-span-5 min-w-0 pr-2">
                              <div className="font-mono font-bold text-xs text-slate-800 dark:text-slate-205 truncate" title={header}>
                                {header}
                              </div>
                              {sampleVal && (
                                <span className="text-[9px] font-mono text-slate-400 uppercase tracking-tight block truncate">
                                  样例: <span className="text-amber-600 dark:text-amber-400">{sampleVal}</span>
                                </span>
                              )}
                            </div>

                            <div className="col-span-6">
                              <select
                                value={destination}
                                onChange={(e) => {
                                  setColumnMappings((prev) => ({
                                    ...prev,
                                    [header]: e.target.value,
                                  }));
                                }}
                                className="w-full px-2.5 py-1.5 text-xs font-semibold bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-750 focus:border-primary-500 focus:outline-none transition-all rounded-lg"
                              >
                                <option value="[skip]" className="text-slate-400 font-mono">
                                  [ 忽略此列不导入 / Ignore Column ]
                                </option>
                                <optgroup label="系统主字段/主键" className="font-bold">
                                  {STANDARD_PROPERTIES.filter((p) => p.isMeta).map((p) => (
                                    <option key={p.key} value={p.key}>
                                      {p.label}
                                    </option>
                                  ))}
                                </optgroup>
                                <optgroup label="标准物理性能参数" className="font-bold">
                                  {STANDARD_PROPERTIES.filter((p) => !p.isMeta).map((p) => (
                                    <option key={p.key} value={p.key}>
                                      {p.label}
                                    </option>
                                  ))}
                                </optgroup>
                                {customColumns.length > 0 && (
                                  <optgroup label="用户自建变量" className="font-bold">
                                    {customColumns.map((c) => (
                                      <option key={c} value={c}>
                                        {c} (自定义属性)
                                      </option>
                                    ))}
                                  </optgroup>
                                )}
                              </select>
                            </div>

                            <div className="col-span-1 flex justify-center">
                              {destination !== "[skip]" ? (
                                <span className={`w-2 h-2 rounded-full ${isRequiredMatched ? "bg-primary-500 animate-ping" : "bg-emerald-500"}`} title={isRequiredMatched ? "主控必需字段" : "正常映射中"} />
                              ) : (
                                <span className="w-1.5 h-1.5 rounded-full bg-slate-300 dark:bg-slate-700" title="忽略" />
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Accordion to dynamically add arbitrary custom variables schema mappings */}
                  <div className="group border border-dashed border-slate-300 dark:border-slate-800 rounded-xl p-3 bg-slate-50/50 dark:bg-slate-900/10">
                    {!showCustomColumnInput ? (
                      <motion.button
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        type="button"
                        onClick={() => setShowCustomColumnInput(true)}
                        className="text-[10px] font-mono font-bold text-primary-600 dark:text-primary-450 hover:underline hover:text-primary-700 flex items-center gap-1.5 uppercase tracking-wide focus:outline-none cursor-pointer"
                      >
                        <PlusCircle size={14} /> + 手动声明新增非标特种参数字段 (Map a custom property)
                      </motion.button>
                    ) : (
                      <div className="flex gap-2 items-center">
                        <input
                          type="text"
                          value={newCustomColumnName}
                          onChange={(e) => setNewCustomColumnName(e.target.value)}
                          placeholder="例如: 极度撕裂指数 (R-Tear)"
                          className="flex-1 px-3 py-1.5 text-xs font-semibold border border-slate-300 dark:border-slate-750 bg-white dark:bg-slate-900 text-slate-950 dark:text-white rounded-lg focus:ring-1 focus:ring-primary-500 outline-none"
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleAddCustomColumn();
                          }}
                        />
                        <motion.button
                          whileHover={{ scale: 1.04 }}
                          whileTap={{ scale: 0.96 }}
                          type="button"
                          onClick={handleAddCustomColumn}
                          className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 font-mono font-bold text-[10px] text-white uppercase tracking-wider rounded-lg cursor-pointer"
                        >
                          确认添加
                        </motion.button>
                        <motion.button
                          whileHover={{ scale: 1.04 }}
                          whileTap={{ scale: 0.96 }}
                          type="button"
                          onClick={() => setShowCustomColumnInput(false)}
                          className="px-3.5 py-1.5 bg-slate-205 dark:bg-slate-800 text-slate-600 dark:text-slate-350 hover:bg-slate-300 text-[10px] font-mono uppercase tracking-wider rounded-lg cursor-pointer"
                        >
                          取消
                        </motion.button>
                      </div>
                    )}
                  </div>

                  {/* De-duplication Policy Control */}
                  <div className="p-4 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl text-left space-y-3.5">
                    <div className="space-y-0.5">
                      <span className="text-xs font-bold text-slate-905 dark:text-slate-100 flex items-center gap-1.5">
                        <Settings size={14} className="text-slate-500" /> 重合牌号冲突消解逻辑 (Deduplication Policy)
                      </span>
                      <p className="text-[10px] text-slate-405 dark:text-slate-450 leading-relaxed font-mono">
                        若您即将合流的牌号名称与物性库已有数据重名，系统将依据以下企业合流机制保障数据一致性：
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-1">
                      {([
                        {
                          key: "merge",
                          title: "🔍 增量合并，局部覆盖",
                          desc: "合流新属性至老牌号中。原记录键值保留，重合属性用新数据更新（最常用且安全）",
                        },
                        {
                          key: "overwrite",
                          title: "♻️ 完全覆盖替换 / Overwrite",
                          desc: "彻底剔除该牌号的已有库数据，完整用此文件录入的新结构取而代之",
                        },
                        {
                          key: "skip",
                          title: "🚫 重合牌号跳过 / Skip",
                          desc: "一旦检索到同名物性数据，则自动静默忽略不合流此行",
                        },
                        {
                          key: "duplicate",
                          title: "📝 并存，作为新记录导入",
                          desc: "忽略同名约束，为其分配新的UUID，在列表中并存记录",
                        }
                      ] as const).map((policy) => (
                        <label
                          key={policy.key}
                          className={`p-3 border rounded-xl cursor-pointer select-none transition-all flex flex-col justify-between ${
                            duplicateAction === policy.key
                              ? "border-primary-500 bg-primary-50/15 dark:bg-primary-950/10 shadow-xs"
                              : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 hover:border-slate-300 dark:hover:border-slate-750"
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <input
                              type="radio"
                              name="policy"
                              checked={duplicateAction === policy.key}
                              onChange={() => setDuplicateAction(policy.key)}
                              className="w-3.5 h-3.5 text-primary-600 focus:ring-primary-500 cursor-pointer"
                            />
                            <span className="text-[11px] font-bold text-slate-900 dark:text-slate-200">
                              {policy.title}
                            </span>
                          </div>
                          <p className="text-[9px] text-slate-450 leading-relaxed font-mono pl-5">
                            {policy.desc}
                          </p>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Actions mapping step Buttons */}
                  <div className="pt-2 flex gap-3">
                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={() => setStep(1)}
                      className="flex-1 py-3 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono font-bold text-[10px] uppercase tracking-widest rounded-xl border border-slate-300 dark:border-slate-700 focus:outline-none cursor-pointer"
                    >
                      <X size={13} /> Back
                    </motion.button>
                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={generateImportProducts}
                      disabled={!Object.values(columnMappings).includes("gradeName")}
                      className={`flex-[2] py-3 font-mono font-bold text-[10px] uppercase tracking-widest rounded-xl focus:outline-none transition-all active:scale-[0.98] shadow-md flex items-center justify-center gap-2 cursor-pointer ${
                        Object.values(columnMappings).includes("gradeName")
                          ? "bg-primary-600 text-white hover:bg-primary-700 shadow-primary-500/10"
                          : "bg-slate-150 dark:bg-slate-900 text-slate-400 cursor-not-allowed border border-slate-300 dark:border-slate-800"
                      }`}
                    >
                      {Object.values(columnMappings).includes("gradeName") ? (
                        <>
                          <CheckCircle size={13} /> 前往数据合法性校验沙盒 (Verify Ingestion)
                        </>
                      ) : (
                        "必须映射一个列至牌号主键才可以进行校验"
                      )}
                    </motion.button>
                  </div>
                </motion.div>
              )}

              {/* Step 3 Granular Quality Validation Sandbox */}
              {step === 3 && (() => {
                const filteredProducts = parsedProducts.filter((p) => {
                  if (!sandboxSearch.trim()) return true;
                  const q = sandboxSearch.toLowerCase().trim();
                  return (
                    p.gradeName.toLowerCase().includes(q) ||
                    p.manufacturer.toLowerCase().includes(q)
                  );
                });

                return (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-6 animate-in fade-in"
                  >
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                      <div className="text-left">
                        <h4 className="text-[10px] font-mono font-bold text-slate-800 dark:text-slate-200 uppercase tracking-widest flex items-center gap-2">
                          <Filter size={14} className="text-primary-500" /> 合流前底层校验安全审查
                        </h4>
                        <p className="text-[9px] font-mono text-slate-400 mt-1 uppercase tracking-tight">
                          DATA VALIDATION & QUALITY CONTROL INSPECTION SANDBOX (双击单元格可极速修改)
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {computedDuplicateOverlapCount > 0 && (
                          <span className="text-[9px] font-mono font-bold bg-amber-50 dark:bg-amber-950/20 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-900/60 px-2 py-0.5 rounded shadow-xs">
                            {computedDuplicateOverlapCount} 个牌号在库重合 ({duplicateAction === "merge" ? "增量更新" : duplicateAction === "overwrite" ? "替换覆盖" : duplicateAction === "skip" ? "自动跳过" : "并存新创"})
                          </span>
                        )}
                        <span className="text-[10px] font-mono font-bold bg-emerald-50 dark:bg-emerald-950/25 text-emerald-600 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-850 px-2 py-0.5 rounded shadow-xs">
                          已验证 {filteredProducts.length} 条记录
                        </span>
                      </div>
                    </div>

                    {/* Search & Filter Bar */}
                    <div className="flex gap-2 items-center">
                      <div className="relative flex-1">
                        <Search size={14} className="absolute left-3 top-2 text-slate-400" />
                        <input
                          type="text"
                          value={sandboxSearch}
                          onChange={(e) => setSandboxSearch(e.target.value)}
                          placeholder={t("importGradeSearchPlaceholder")}
                          className="w-full pl-9 pr-3 py-1.5 font-sans font-medium text-xs border border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 rounded-xl outline-none focus:ring-1 focus:ring-primary-500 transition-all shadow-xs"
                        />
                      </div>
                      {sandboxSearch && (
                        <motion.button
                          whileHover={{ scale: 1.04 }}
                          whileTap={{ scale: 0.96 }}
                          type="button"
                          onClick={() => setSandboxSearch("")}
                          className="px-3 py-1.5 bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:text-slate-800 hover:bg-slate-200 text-xs font-mono font-semibold rounded-lg cursor-pointer"
                        >
                          {t("clearFilter", "清除过滤")}
                        </motion.button>
                      )}
                    </div>

                    {/* Sandboxed data grid of parsed results */}
                    <div className="max-h-72 overflow-y-auto custom-scrollbar border border-slate-300 dark:border-slate-705 bg-white dark:bg-slate-950 rounded-xl shadow-inner scroll-smooth">
                      <table className="w-full text-left border-collapse table-auto">
                        <thead className="sticky top-0 bg-slate-50 dark:bg-slate-900 shadow-xs z-10 border-b border-slate-300 dark:border-slate-700">
                          <tr className="text-[9px] font-mono font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest">
                            <th className="px-4 py-2.5">{t("importGradeHeader")}</th>
                            <th className="px-4 py-2.5">{t("importMfrHeader")}</th>
                            <th className="px-4 py-2.5">{t("importPropertiesHeader")}</th>
                            <th className="px-4 py-2.5 text-center">{t("importStatusHeader")}</th>
                            <th className="px-4 py-2 text-center">{t("importActionHeader")}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-150 dark:divide-slate-800/50">
                          {filteredProducts.map((p) => {
                            const isNewDuplicate = (allProducts || []).some(
                              (x) => x.gradeName.toUpperCase() === p.gradeName.toUpperCase()
                            );
                            const totalProps = Object.keys(p.properties).length;
                            const warnings = getProductValidationWarnings(p, t);

                            return (
                              <tr key={p.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/10 transition-colors group">
                                <td className="px-4 py-2.5">
                                  {editingCell?.id === p.id && editingCell?.field === "gradeName" ? (
                                    <input
                                      type="text"
                                      value={p.gradeName}
                                      onChange={(e) => handleUpdateParsedProduct(p.id, "gradeName", e.target.value)}
                                      onBlur={() => setEditingCell(null)}
                                      onKeyDown={(e) => { if (e.key === "Enter") setEditingCell(null); }}
                                      autoFocus
                                      className="px-2 py-0.5 font-mono text-xs text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-900 border border-primary-500 rounded outline-none"
                                    />
                                  ) : (
                                    <div 
                                      className="font-mono font-bold text-xs text-slate-800 dark:text-slate-200 truncate max-w-[190px] group-hover:text-primary-600 transition-colors cursor-pointer" 
                                      title={t("doubleClickToEdit")}
                                      onDoubleClick={() => setEditingCell({ id: p.id, field: "gradeName" })}
                                    >
                                      {p.gradeName} <span className="opacity-0 group-hover:opacity-100 text-[9px] text-primary-500 ml-1">✏️</span>
                                    </div>
                                  )}
                                </td>
                                <td className="px-4 py-2.5">
                                  {editingCell?.id === p.id && editingCell?.field === "manufacturer" ? (
                                    <input
                                      type="text"
                                      value={p.manufacturer}
                                      onChange={(e) => handleUpdateParsedProduct(p.id, "manufacturer", e.target.value)}
                                      onBlur={() => setEditingCell(null)}
                                      onKeyDown={(e) => { if (e.key === "Enter") setEditingCell(null); }}
                                      autoFocus
                                      className="px-2 py-0.5 font-mono text-xs text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-900 border border-primary-500 rounded outline-none"
                                    />
                                  ) : (
                                    <div 
                                      className="text-[10px] font-mono text-slate-500 truncate max-w-[140px] cursor-pointer" 
                                      title={t("doubleClickToEdit")}
                                      onDoubleClick={() => setEditingCell({ id: p.id, field: "manufacturer" })}
                                    >
                                      {p.manufacturer} <span className="opacity-0 group-hover:opacity-100 text-[9px] text-primary-500 ml-1">✏️</span>
                                    </div>
                                  )}
                                </td>
                                <td className="px-4 py-2.5 pr-2">
                                  <div className="flex flex-wrap gap-1 max-w-[240px]">
                                    {totalProps > 0 ? (
                                      Object.keys(p.properties).map((propK) => {
                                        const isEditingProp = editingCell?.id === p.id && editingCell?.field === propK;
                                        return (
                                          <span 
                                            key={propK}
                                            title={t("doubleClickValueToEdit")}
                                            className="text-[8px] font-mono px-1.5 py-0.5 bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-350 border border-slate-200 dark:border-slate-800 rounded flex items-center gap-1 cursor-pointer hover:border-primary-400 group/item transition-colors"
                                            onDoubleClick={() => setEditingCell({ id: p.id, field: propK })}
                                          >
                                            {isEditingProp ? (
                                              <input
                                                type="text"
                                                defaultValue={String(p.properties[propK]?.value)}
                                                onBlur={(e) => {
                                                  handleUpdateParsedProperty(p.id, propK, e.target.value);
                                                  setEditingCell(null);
                                                }}
                                                onKeyDown={(e) => {
                                                  if (e.key === "Enter") {
                                                    handleUpdateParsedProperty(p.id, propK, (e.target as HTMLInputElement).value);
                                                    setEditingCell(null);
                                                  }
                                                }}
                                                autoFocus
                                                className="w-12 px-0.5 text-[8px] font-mono border border-primary-500 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 rounded outline-none"
                                              />
                                            ) : (
                                              <>
                                                <span className="font-semibold">{propK}:</span>
                                                <span>{String(p.properties[propK]?.value)}</span>
                                              </>
                                            )}
                                          </span>
                                        );
                                      })
                                    ) : (
                                      <span className="text-[8px] font-mono text-rose-500 dark:text-rose-400">
                                        {t("noPropertiesExtracted", "无物性性能提取")}
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="px-4 py-2.5 text-center">
                                  <div className="flex flex-col gap-1 items-center">
                                    {isNewDuplicate ? (
                                      <span 
                                        className="text-[8px] font-mono font-bold text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 px-2 py-0.5 rounded cursor-help"
                                        title={t("duplicateWarnMsg").replace("{action}", duplicateAction)}
                                      >
                                        {t("duplicateConflict", "共用牌号冲突重合")}
                                      </span>
                                    ) : (
                                      <span className="text-[8px] font-mono font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-100 px-2 py-0.5 rounded">
                                        {t("pass", "物理安全通过")}
                                      </span>
                                    )}
                                    {warnings.map((w, idx) => (
                                      <span 
                                        key={idx} 
                                        className="text-[7px] font-sans text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-955/35 border border-rose-100 px-1 py-0.5 rounded flex items-center gap-0.5"
                                        title={w}
                                      >
                                        ⚠️ {t("valueAnomalyDev", "数值明显常规偏离")}
                                      </span>
                                    ))}
                                  </div>
                                </td>
                                <td className="px-4 py-2.5 text-center">
                                  <motion.button
                                    whileHover={{ scale: 1.1, color: "#f43f5e" }}
                                    whileTap={{ scale: 0.9 }}
                                    onClick={() => handleRemoveSandboxProduct(p.id)}
                                    className="p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded transition-colors cursor-pointer"
                                    title={t("excludeTempBtnTitle")}
                                  >
                                    <Trash2 size={12} />
                                  </motion.button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                      {filteredProducts.length === 0 && (
                        <div className="p-8 text-center text-xs font-mono text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                          {t("noStagedProducts", "无可检索匹配的沙盒内记录。")}
                        </div>
                      )}
                    </div>

                    <div className="pt-2 flex gap-3">
                      <motion.button
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                        onClick={() => setStep(2)}
                        className="flex-1 py-3.5 bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 font-mono font-bold text-[10px] uppercase tracking-widest shadow-sm flex items-center justify-center gap-2 rounded-xl border border-slate-300 dark:border-slate-700 cursor-pointer"
                      >
                        <X size={13} /> Back
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                        disabled={filteredProducts.length === 0}
                        onClick={() => {
                          if (onImport) onImport(filteredProducts);
                          setStep(4); // Transfer to elegant completion screen
                        }}
                        className="flex-[2.5] py-3.5 bg-primary-600 hover:bg-primary-700 disabled:opacity-40 text-white font-mono font-bold text-[10px] uppercase tracking-widest shadow-lg flex items-center justify-center gap-2 rounded-xl border border-primary-500 shadow-primary-500/20 cursor-pointer"
                      >
                        <CheckCircle size={14} /> {t("mergeAndImportBtn").replace("{count}", String(filteredProducts.length))}
                      </motion.button>
                    </div>
                  </motion.div>
                );
              })()}

              {/* Success celebration Step */}
              {step === 4 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                  className="flex flex-col items-center justify-center py-6 text-center"
                >
                  <div className="w-16 h-16 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-805 flex items-center justify-center mb-6 rounded-2xl shadow-sm">
                    <CheckCircle className="text-emerald-600 w-8 h-8" />
                  </div>
                  <h4 className="text-slate-900 dark:text-white font-serif font-bold text-xl mb-1 tracking-tight">
                    {t("success", "合流导入服务自举成功")}
                  </h4>
                  <p className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest mb-6">
                    <span className="text-emerald-600 dark:text-emerald-400">
                      {parsedProducts.length} RECORDS MERGED & ENRICHED SECURELY
                    </span>
                  </p>

                  <div className="bg-slate-50 dark:bg-slate-900/50 border border-slate-205 dark:border-slate-800 rounded-xl p-4 w-full max-w-sm mb-6 text-left space-y-2">
                    <h5 className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-600 dark:text-slate-350">
                      {t("dataIngestionTelemetry", "物性摄取审计 (Data Ingestion Telemetry)")}
                    </h5>
                    <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                      <div>{t("successImportRecords")}: <span className="text-slate-800 dark:text-white font-bold">{parsedProducts.length} {t("itemsUnit", "条")}</span></div>
                      <div>{t("successOverlapConflicts")}: <span className="text-slate-850 dark:text-white font-bold">{computedDuplicateOverlapCount} {t("countUnit", "个")}</span></div>
                      <div>{t("successInjectMode")}: <span className="text-slate-800 dark:text-white font-bold">{isExperimentalImport ? t("experimentalLabData", "自测实验数据") : t("mainMerge", "主厂合流")}</span></div>
                      <div>{t("successValidationLevel")}: <span className="text-emerald-600 font-bold">100% EXCELLENT</span></div>
                    </div>
                  </div>

                  <div className="flex gap-3 w-full">
                    <motion.button
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                      onClick={onClose}
                      className="flex-1 px-4 py-3.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-mono font-bold text-[10px] uppercase tracking-widest shadow-md transition-all focus:outline-none rounded-xl border border-slate-800 dark:border-slate-200 cursor-pointer"
                    >
                      {t("finish", "完成并返回数据仪表盘")}
                    </motion.button>
                  </div>
                </motion.div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
});

ImportModal.displayName = "ImportModal";
