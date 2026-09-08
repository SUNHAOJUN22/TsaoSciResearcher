import { logger } from '@/lib/logger';
import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  X,
  Shield,
  Users,
  Activity,
  Trash2,
  Database,
  CheckCircle2,
  Briefcase,
  FileText,
  ExternalLink,
  Sparkles,
  ChevronDown,
  UploadCloud,
  Loader2
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import { User as UserType } from '@/types/index';
import api from '@/lib/adapters';
import { PRODUCT_CATALOG } from '@/config/constants';
import { safeStorage } from "@/lib/utils";
import { UserAvatar } from "@/components/ui/UserAvatar";

interface AdminModalProps {
  isOpen: boolean;
  onClose: () => void;
}

function isDemoUser(value: unknown): value is UserType {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<UserType>;
  return Boolean(
    typeof candidate.id === 'string' &&
    typeof candidate.name === 'string' &&
    typeof candidate.email === 'string' &&
    candidate.role &&
    ['admin', 'editor', 'viewer'].includes(candidate.role),
  );
}

export const AdminModal: React.FC<AdminModalProps> = React.memo(({ isOpen, onClose }) => {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<
    "users" | "projects" | "docs" | "system"
  >("users");
  const [users, setUsers] = useState<UserType[]>([]);
  const stats = {
    dbSize: "Browser managed",
    uptime: "Current session",
  };
  const [isSeeding, setIsSeeding] = useState(false);
  const [seedProgress, setSeedProgress] = useState(0);

  const handleSeedData = async () => {
    try {
      setIsSeeding(true);
      setSeedProgress(10);
      
      const batchSize = 50;
      for (let i = 0; i < PRODUCT_CATALOG.length; i += batchSize) {
        const batch = PRODUCT_CATALOG.slice(i, i + batchSize);
        await api.batchCreate(batch);
        setSeedProgress(Math.min(100, Math.floor(10 + ((i + batchSize) / PRODUCT_CATALOG.length) * 90)));
      }
      
      setSeedProgress(100);
      setTimeout(() => {
        setIsSeeding(false);
        setSeedProgress(0);
        alert(t("dbSeedSuccess"));
        window.location.reload();
      }, 1000);
    } catch (e) {
      logger.error(e);
      alert(t("dbSeedError"));
      setIsSeeding(false);
      setSeedProgress(0);
    }
  };

  const loadUsers = useCallback(() => {
    try {
      const saved = safeStorage.local.getItem("resindb-users");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          const finalUsers = parsed.filter(isDemoUser);
          setUsers(finalUsers);
          return;
        }
      }
      
      const defaultUsers: UserType[] = [
        { id: "demo-admin", name: "Demo Admin", email: "admin@example.invalid", role: "admin" },
        { id: "demo-editor", name: "Demo Editor", email: "editor@example.invalid", role: "editor" },
        { id: "demo-viewer", name: "Demo Viewer", email: "viewer@example.invalid", role: "viewer" },
      ];
      setUsers(defaultUsers);
      safeStorage.local.setItem("resindb-users", JSON.stringify(defaultUsers));
    } catch (e) {
      logger.error("Failed to load users:", e);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleDeleteUser = (id: string) => {
    if (id === "demo-admin") return;
    const updated = users.filter((u) => u.id !== id);
    setUsers(updated);
    try {
      safeStorage.local.setItem("resindb-users", JSON.stringify(updated));
    } catch (e) {
      logger.error("Failed to persist user deletion:", e);
    }
  };

  const handleUpdateRole = (id: string, role: UserType["role"]) => {
    const updated = users.map((u) => (u.id === id ? { ...u, role } : u));
    setUsers(updated);
    try {
      safeStorage.local.setItem("resindb-users", JSON.stringify(updated));
    } catch (e) {
      logger.error("Failed to persist role update:", e);
    }
  };

  const mockProjects = [
    {
      id: 1,
      name: t("projName1"),
      lead: t("projLead1"),
      progress: 75,
      status: "Active",
    },
    {
      id: 2,
      name: t("projName2"),
      lead: t("projLead2"),
      progress: 40,
      status: "Active",
    },
    {
      id: 3,
      name: t("projName3"),
      lead: t("projLead3"),
      progress: 100,
      status: "Completed",
    },
  ];

  const mockDocs = [
    {
      id: 1,
      title: t("adminDocTitleManual"),
      type: "PDF",
      date: "2024-01-10",
    },
    {
      id: 2,
      title: t("adminDocTitleRegulation"),
      type: "DOC",
      date: "2023-12-20",
    },
    { id: 3, title: t("adminDocTitleSecurity"), type: "PDF", date: "2023-11-15" },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="admin-modal-overlay-container"
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
        >
          <motion.div
            key="admin-modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          ></motion.div>
          <motion.div
            key="admin-modal-content"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.4, bounce: 0 }}
            className="relative w-full max-w-5xl bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 flex flex-col h-[90vh] md:h-[700px] shadow-2xl rounded-2xl md:rounded-3xl overflow-hidden"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-300 dark:border-slate-700 flex items-center justify-between bg-slate-900 dark:bg-slate-950 relative overflow-hidden shrink-0">
              <div className="flex items-center gap-4 relative z-10">
                <div className="p-2 bg-primary-600 text-white border border-primary-700 rounded-xl shadow-inner">
                  <Shield size={20} />
                </div>
                <div>
                  <h3 className="text-sm font-serif font-bold text-white tracking-tight leading-none mb-1">
                    {t("adminPanel")}
                  </h3>
                  <p className="text-[10px] text-slate-400 font-mono uppercase tracking-widest">
                    {t("adminConsole")}
                  </p>
                </div>
              </div>
              <motion.button
                whileHover={{ scale: 1.1, rotate: 90 }}
                whileTap={{ scale: 0.9 }}
                onClick={onClose}
                className="p-2 bg-white/5 backdrop-blur-md border border-white/10 hover:bg-rose-500/20 hover:border-rose-500/30 hover:text-rose-500 text-slate-400 rounded-xl transition-all z-10"
              >
                <X size={16} />
              </motion.button>
            </div>

            <div className="flex flex-col md:flex-row flex-1 overflow-hidden">
              {/* Sidebar Tabs */}
              <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 p-3 md:p-4 flex md:flex-col gap-1.5 overflow-x-auto md:overflow-y-auto no-scrollbar md:custom-scrollbar relative shrink-0">
                {(
                  [
                    { id: "users", icon: Users, label: t("userRegistry") },
                    { id: "projects", icon: Briefcase, label: t("rdProjects") },
                    { id: "docs", icon: FileText, label: t("docRepo") },
                    { id: "system", icon: Activity, label: t("systemInfra") },
                  ] as const
                ).map((tab) => (
                  <motion.button
                    key={tab.id}
                    whileHover={{
                      x: 4,
                      backgroundColor:
                        activeTab === tab.id
                          ? undefined
                          : "rgba(241, 245, 249, 0.5)",
                    }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 md:gap-3 px-3 md:px-4 py-2 md:py-3 text-[9px] md:text-[10px] font-mono font-bold uppercase tracking-widest transition-all rounded-xl md:rounded-2xl focus:outline-none border relative overflow-hidden shrink-0 ${activeTab === tab.id ? "text-white border-primary-600 shadow-lg shadow-primary-500/20" : "text-slate-500 bg-white/50 dark:bg-slate-950/50 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"}`}
                  >
                    {activeTab === tab.id && (
                      <motion.div
                        layoutId="activeTabBg"
                        className="absolute inset-0 bg-primary-600 z-0"
                        transition={{
                          type: "spring",
                          bounce: 0.2,
                          duration: 0.6,
                        }}
                      />
                    )}
                    <tab.icon size={14} className="md:size-4 relative z-10" />
                    <span className="relative z-10 whitespace-nowrap">
                      {tab.label}
                    </span>
                  </motion.button>
                ))}

                <div className="hidden md:block pt-8 px-1">
                  <p className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest mb-4 px-1">
                    {t("announcements")}
                  </p>
                  <div className="space-y-3">
                    <div className="p-3 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm relative overflow-hidden group">
                      <p className="text-[10px] font-mono font-bold text-slate-800 dark:text-white relative z-10">
                        {t("announcementTitle")}
                      </p>
                      <p className="text-[10px] font-mono text-slate-500 dark:text-slate-400 mt-1 leading-relaxed relative z-10">
                        {t("announcementContent")}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar bg-white dark:bg-slate-950 relative">
                <AnimatePresence mode="wait">
                  {activeTab === "users" && (
                    <motion.div
                      key="users"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className="space-y-4"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">
                          {t("userRegistry")}
                        </h4>
                        <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                          {users.length} TOTAL
                        </span>
                      </div>
                      <div className="grid grid-cols-1 gap-2">
                        {users.map((u, idx) => (
                          <motion.div
                            key={u.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: idx * 0.03 }}
                            className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl group transition-all hover:border-slate-400 dark:hover:border-slate-600 shadow-sm hover:shadow-md"
                          >
                            <div className="flex items-center gap-4">
                              <motion.div
                                whileHover={{ scale: 1.1, rotate: 5 }}
                                className="w-12 h-12 border border-slate-200 dark:border-slate-700 overflow-hidden rounded-2xl shadow-sm"
                              >
                                <UserAvatar name={u.name} avatar={u.avatar} className="h-full w-full rounded-none text-xs" />
                              </motion.div>
                              <div>
                                <p className="text-[13px] font-bold text-slate-800 dark:text-slate-100 tracking-tight leading-none mb-1.5">
                                  {u.name}
                                </p>
                                <p className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                                  {u.email}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-3">
                              <div className="relative">
                                <select
                                  value={u.role}
                                  onChange={(e) =>
                                    handleUpdateRole(
                                      u.id,
                                      e.target.value as UserType["role"],
                                    )
                                  }
                                  className="appearance-none bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-[10px] font-mono font-bold uppercase tracking-widest pl-3 pr-8 py-2 outline-none focus:border-primary-500 transition-all cursor-pointer shadow-sm hover:border-slate-400"
                                >
                                  <option value="admin">Admin</option>
                                  <option value="editor">Editor</option>
                                  <option value="viewer">Viewer</option>
                                </select>
                                <ChevronDown
                                  size={12}
                                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
                                />
                              </div>
                              <motion.button
                                whileHover={{
                                  scale: 1.1,
                                  backgroundColor: "rgba(225, 29, 72, 0.1)",
                                }}
                                whileTap={{ scale: 0.9 }}
                                onClick={() => handleDeleteUser(u.id)}
                                className="p-2 text-slate-400 hover:text-rose-600 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm transition-all hover:border-rose-500/50"
                                title="Remove User"
                              >
                                <Trash2 size={16} />
                              </motion.button>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </motion.div>
                  )}

                  {activeTab === "projects" && (
                    <motion.div
                      key="projects"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.15 }}
                      className="space-y-4"
                    >
                      <h4 className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest mb-4">
                        {t("rdProjects")}
                      </h4>
                      <div className="grid grid-cols-1 gap-3">
                        {mockProjects.map((p) => (
                          <motion.div
                            key={p.id}
                            whileHover={{ scale: 1.01, x: 4 }}
                            whileTap={{ scale: 0.99 }}
                            className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm transition-all hover:shadow-md cursor-pointer hover:border-primary-500/50 dark:hover:border-primary-400/50"
                          >
                            <div className="flex justify-between items-start mb-4">
                              <div className="flex-1 min-w-0 pr-4">
                                <h5 className="text-sm font-serif font-bold text-slate-800 dark:text-slate-100 tracking-tight truncate mb-1">
                                  {p.name}
                                </h5>
                                <div className="flex items-center gap-2">
                                  <div className="w-1.5 h-1.5 rounded-full bg-primary-500" />
                                  <p className="text-[9px] font-mono font-bold text-slate-500 uppercase tracking-widest">
                                    {t("projectLead")}: {p.lead}
                                  </p>
                                </div>
                              </div>
                              <span
                                className={`text-[8px] px-2 py-0.5 border font-mono font-bold uppercase tracking-widest rounded-md shadow-sm ${p.status === "Completed" ? "bg-emerald-50 text-emerald-600 border-emerald-200" : "bg-blue-50 text-blue-600 border-blue-200"}`}
                              >
                                {p.status === "Completed"
                                  ? t("completed")
                                  : t("active")}
                              </span>
                            </div>
                            <div className="space-y-2">
                              <div className="flex justify-between items-end">
                                <span className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                                  {t("progress")}
                                </span>
                                <span className="text-[10px] font-mono font-bold text-emerald-600">
                                  {p.progress}%
                                </span>
                              </div>
                              <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-800 overflow-hidden rounded-full">
                                <motion.div
                                  initial={{ width: 0 }}
                                  animate={{ width: `${p.progress}%` }}
                                  transition={{
                                    duration: 1.5,
                                    ease: "easeOut",
                                  }}
                                  className="h-full bg-primary-600"
                                />
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </motion.div>
                  )}

                  {activeTab === "docs" && (
                    <motion.div
                      key="docs"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.15 }}
                      className="space-y-4"
                    >
                      <h4 className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest mb-4">
                        {t("docRepo")}
                      </h4>
                      <div className="bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
                        {mockDocs.map((doc) => (
                          <div
                            key={doc.id}
                            className="flex items-center justify-between p-4 border-b last:border-none border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors group"
                          >
                            <div className="flex items-center gap-4">
                              <div
                                className={`p-2 rounded-xl border ${doc.type === "PDF" ? "bg-rose-50 text-rose-500 border-rose-100 dark:bg-rose-900/20 dark:border-rose-800/50" : "bg-blue-50 text-blue-500 border-blue-100 dark:bg-blue-900/20 dark:border-blue-800/50"}`}
                              >
                                <FileText size={16} />
                              </div>
                              <div>
                                <p className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 tracking-tight leading-none mb-1">
                                  {doc.title}
                                </p>
                                <p className="text-[9px] text-slate-400 font-mono font-bold uppercase tracking-widest">
                                  {doc.date} • {doc.type} Document
                                </p>
                              </div>
                            </div>
                            <motion.button
                              whileHover={{ scale: 1.1, x: 2 }}
                              whileTap={{ scale: 0.9 }}
                              className="p-2 rounded-lg text-slate-400 hover:text-primary-600 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 transition-all hover:shadow-sm"
                            >
                              <ExternalLink size={14} />
                            </motion.button>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}

                  {activeTab === "system" && (
                    <motion.div
                      key="system"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.15 }}
                      className="space-y-6"
                    >
                      <h4 className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">
                        {t("systemInfra")}
                      </h4>
                      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                        <motion.div
                          whileHover={{ scale: 1.02, y: -4 }}
                          className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl relative overflow-hidden group shadow-sm transition-all hover:shadow-md hover:border-primary-500/50 cursor-default"
                        >
                          <div className="flex items-center gap-3 text-slate-400 mb-3">
                            <div className="p-2 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-sm">
                              <Database size={14} />
                            </div>
                            <span className="text-[9px] font-mono font-bold uppercase tracking-widest">
                              {t("databaseSize")}
                            </span>
                          </div>
                          <p className="text-2xl font-mono font-bold text-slate-900 dark:text-white tracking-tighter">
                            {stats.dbSize}
                          </p>
                        </motion.div>
                        <motion.div
                          whileHover={{ scale: 1.02, y: -4 }}
                          className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl relative overflow-hidden group shadow-sm transition-all hover:shadow-md hover:border-primary-500/50 cursor-default"
                        >
                          <div className="flex items-center gap-3 text-slate-400 mb-3">
                            <div className="p-2 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-sm">
                              <Activity size={14} />
                            </div>
                            <span className="text-[9px] font-mono font-bold uppercase tracking-widest">
                              {t("uptime")}
                            </span>
                          </div>
                          <p className="text-2xl font-mono font-bold text-slate-900 dark:text-white tracking-tighter">
                            {stats.uptime}
                          </p>
                        </motion.div>
                        <motion.div
                          whileHover={{ scale: 1.02, y: -4 }}
                          className="col-span-2 lg:col-span-1 p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl relative overflow-hidden group shadow-sm transition-all hover:shadow-md hover:border-primary-500/50 cursor-default flex flex-col justify-between"
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-3 text-slate-400">
                              <div className="p-2 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-sm">
                                <Users size={14} />
                              </div>
                              <span className="text-[9px] font-mono font-bold uppercase tracking-widest">
                                {t("systemAdmin")}
                              </span>
                            </div>
                            <span className="text-[8px] font-mono font-bold uppercase text-primary-500 tracking-widest px-2 py-0.5 rounded border border-primary-500/30 bg-primary-500/10">Developer</span>
                          </div>
                          <div className="flex items-center gap-3 mt-1">
                            <UserAvatar name="Repository" className="h-10 w-10 shrink-0 rounded-full border-2 border-primary-500 text-[9px] shadow-sm" />
                            <div>
                              <p className="text-sm font-bold text-slate-900 dark:text-white tracking-tight leading-none mb-1">Repository</p>
                              <p className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Local demo administration</p>
                            </div>
                          </div>
                        </motion.div>
                      </div>

                      <motion.div
                        whileHover={{ scale: 1.01 }}
                        className="p-6 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl relative overflow-hidden shadow-sm transition-all flex items-center justify-between"
                      >
                        <div>
                          <h5 className="text-[10px] font-mono font-bold text-primary-600 uppercase tracking-widest mb-1">
                            {t("dataMigration")}
                          </h5>
                          <p className="text-xs text-slate-500 font-mono">
                            {t("dataMigrationDesc").replace("{count}", String(PRODUCT_CATALOG.length))}
                          </p>
                        </div>
                        <motion.button
                          whileHover={isSeeding ? {} : { scale: 1.02 }}
                          whileTap={isSeeding ? {} : { scale: 0.98 }}
                          onClick={handleSeedData}
                          disabled={isSeeding}
                          className="px-4 py-2 bg-primary-600 text-white rounded-xl text-xs font-bold font-mono tracking-widest uppercase hover:bg-primary-500 transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                        >
                          {isSeeding ? <Loader2 size={14} className="animate-spin" /> : <UploadCloud size={14} />}
                          {isSeeding ? `${seedProgress}%` : t("seedDatabase")}
                        </motion.button>
                      </motion.div>

                      <motion.div
                        whileHover={{ scale: 1.01 }}
                        className="p-6 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl relative overflow-hidden shadow-sm transition-all hover:shadow-md hover:border-emerald-500/50 cursor-default"
                      >
                        <div className="flex items-center justify-between mb-4 relative z-10">
                           <div className="flex items-center gap-3">
                            <div className="p-2 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800/50 text-emerald-600 shadow-sm">
                              <CheckCircle2 size={16} />
                            </div>
                            <h5 className="text-[10px] font-mono font-bold text-emerald-800 dark:text-emerald-400 uppercase tracking-widest">
                              {t("governance")}
                            </h5>
                          </div>
                          <span className="text-xs font-mono font-bold text-emerald-600">
                            88%
                          </span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden relative z-10">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: "88%" }}
                            transition={{ duration: 2, ease: "easeOut" }}
                            className="h-full bg-emerald-500"
                          />
                        </div>
                        <p className="text-[10px] font-mono font-bold text-slate-500 mt-4 flex items-center gap-2 relative z-10">
                          <Sparkles size={12} className="text-emerald-500" />
                          {t("governanceDesc")}
                        </p>
                      </motion.div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 flex justify-end shrink-0">
              <motion.button
                whileHover={{ scale: 1.05, backgroundColor: "#000" }}
                whileTap={{ scale: 0.95 }}
                onClick={onClose}
                className="px-8 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-mono font-bold text-[10px] uppercase tracking-widest transition-all rounded-xl shadow-lg"
              >
                {t("finish")}
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
});
