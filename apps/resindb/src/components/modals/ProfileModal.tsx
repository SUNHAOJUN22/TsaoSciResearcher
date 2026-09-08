import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  X,
  Save,
  User,
  Mail,
  Camera,
  CheckCircle2,
  Loader2,
  ShieldCheck,
  RotateCcw,
  Palette,
  Moon,
  Sun,
} from "lucide-react";
import { User as UserType } from '@/types/index';
import { useLanguage } from "@/contexts/LanguageContext";
import { useTheme, ColorTheme } from "@/contexts/ThemeContext";
import { useUI } from "@/contexts/UIContext";
import { UserAvatar } from "@/components/ui/UserAvatar";

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: UserType | null;
  onSave: (updatedUser: Partial<UserType>) => void;
  onAddToast: (type: "success" | "error" | "info", message: string) => void;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  user,
  onSave,
  onAddToast,
}) => {
  const { t } = useLanguage();
  const { clickFeedbackEnabled, setClickFeedbackEnabled } = useUI();
  const { colorTheme, setColorTheme, theme, toggleTheme } = useTheme();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [avatar, setAvatar] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    if (user) {
      setName(user.name);
      setEmail(user.email);
      setAvatar(user.avatar || "");
      setShowSuccess(false);
    }
  }, [user]);

  const handleLocalUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      onAddToast("error", "Only PNG, JPEG and WebP avatars are supported.");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      onAddToast("error", t("fileTooLarge"));
      return;
    }
    const reader = new FileReader();
    reader.onloadend = () => setAvatar(typeof reader.result === 'string' ? reader.result : '');
    reader.readAsDataURL(file);
  };

  const resetToDefault = () => {
    setAvatar("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);

    setTimeout(() => {
      onSave({ name: name.trim(), email: email.trim(), avatar: avatar || undefined });
      setIsSaving(false);
      setShowSuccess(true);

      setTimeout(() => {
        onClose();
      }, 1500);
    }, 1000);
  };

  return (
    <AnimatePresence>
      {isOpen && user && (
        <motion.div
          key="profile-modal-overlay-container"
          className="fixed inset-0 z-[160] flex items-center justify-center p-4"
        >
          <motion.div
            key="profile-modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm"
            onClick={onClose}
          ></motion.div>
          <motion.div
            key="profile-modal-content"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.4, bounce: 0 }}
            className="relative w-full max-w-lg bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 shadow-2xl overflow-hidden rounded-[2.5rem]"
          >
            <div className="px-6 py-4 border-b border-slate-300 dark:border-slate-700 flex items-center justify-between bg-slate-900 dark:bg-slate-950 relative overflow-hidden shrink-0">
              <div className="flex items-center gap-3 relative z-10">
                <div className="p-2 bg-primary-600 text-white border border-primary-700 rounded-xl">
                  <User size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-serif font-bold text-white tracking-tight leading-none mb-1">
                    {t("editProfile")}
                  </h3>
                  <p className="text-[10px] text-slate-400 font-mono uppercase tracking-widest">
                    {t("userSettings")}
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
                className="p-2 bg-white/10 backdrop-blur-md border border-white/20 text-white transition-all focus:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 z-10 rounded-xl"
              >
                <X size={16} />
              </motion.button>
            </div>

            {showSuccess ? (
              <div className="p-12 flex flex-col items-center justify-center text-center animate-in fade-in zoom-in-95">
                <div className="w-16 h-16 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-emerald-600 flex items-center justify-center mb-6 shadow-sm">
                  <CheckCircle2 size={32} />
                </div>
                <h4 className="text-lg font-serif font-bold text-slate-900 dark:text-white mb-2 tracking-tight">
                  {t("updateSuccess")}
                </h4>
                <p className="text-[10px] font-mono font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest">
                  {t("securityNote")}
                </p>
              </div>
            ) : (
              <div className="flex flex-col bg-white dark:bg-slate-950">
                <form onSubmit={handleSubmit} className="p-8 space-y-6">
                  <div className="flex flex-col items-center gap-6 mb-2">
                    <div className="relative group/avatar">
                      <motion.div
                        whileHover={{ scale: 1.05 }}
                        className="w-28 h-28 overflow-hidden rounded-[2rem] border-2 border-slate-200 dark:border-slate-800 shadow-2xl relative group cursor-pointer"
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <UserAvatar
                          name={name}
                          avatar={avatar}
                          alt="Profile avatar preview"
                          className="h-full w-full rounded-none text-xl"
                        />
                        <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <Camera size={24} className="text-white" />
                        </div>
                      </motion.div>
                      <div className="absolute -bottom-2 flex gap-2 left-1/2 -translate-x-1/2">
                        <motion.button
                          whileHover={{
                            scale: 1.1,
                            backgroundColor: "rgba(79, 70, 229, 1)",
                          }}
                          whileTap={{ scale: 0.9 }}
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="p-2.5 bg-primary-600 text-white border border-primary-700 shadow-xl focus:outline-none rounded-xl"
                          title={t("changeAvatar")}
                        >
                          <Camera size={16} />
                        </motion.button>
                        <motion.button
                          whileHover={{
                            scale: 1.1,
                            backgroundColor: "rgba(241, 245, 249, 1)",
                          }}
                          whileTap={{ scale: 0.9 }}
                          type="button"
                          onClick={resetToDefault}
                          className="p-2.5 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border border-slate-300 dark:border-slate-700 shadow-xl hover:text-primary-600 focus:outline-none rounded-xl"
                          title={t("resetDefault")}
                        >
                          <RotateCcw size={16} />
                        </motion.button>
                      </div>
                      <input
                        type="file"
                        ref={fileInputRef}
                        className="hidden"
                        accept="image/png,image/jpeg,image/webp"
                        onChange={handleLocalUpload}
                      />
                    </div>
                    <p className="max-w-sm text-center text-[10px] font-mono leading-5 text-slate-500 dark:text-slate-400">
                      Avatar images stay in this browser session. Use PNG, JPEG or WebP files up to 2 MB.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div className="space-y-2">
                      <label className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest ml-1">
                        {t("username")}
                      </label>
                      <div className="relative group">
                        <User
                          size={14}
                          className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary-500 transition-colors"
                        />
                        <motion.input
                          whileFocus={{
                            scale: 1.01,
                            boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                          }}
                          type="text"
                          required
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          className="w-full pl-11 pr-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-mono font-bold outline-none focus:border-primary-500 focus:ring-4 focus:ring-primary-500/5 transition-all dark:text-slate-200"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest ml-1">
                        {t("email")}
                      </label>
                      <div className="relative group">
                        <Mail
                          size={14}
                          className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary-500 transition-colors"
                        />
                        <motion.input
                          whileFocus={{
                            scale: 1.01,
                            boxShadow: "0 0 0 4px rgba(79, 70, 229, 0.1)",
                          }}
                          type="email"
                          required
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="w-full pl-11 pr-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-xs font-mono font-bold outline-none focus:border-primary-500 focus:ring-4 focus:ring-primary-500/5 transition-all dark:text-slate-200"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-800">
                    <div className="flex items-center gap-2 mb-2">
                       <Palette size={14} className="text-slate-400" />
                       <label className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                         {t("appearanceSettings")}
                       </label>
                    </div>
                    
                    <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
                      <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
                        {t("colorTheme")}
                      </span>
                      <select 
                        value={colorTheme}
                        onChange={(e) => setColorTheme(e.target.value as ColorTheme)}
                        className="bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono font-bold uppercase tracking-widest pl-3 pr-8 py-1.5 outline-none focus:border-primary-500 transition-all cursor-pointer shadow-sm text-slate-700 dark:text-slate-300"
                      >
                        <option value="indigo">{t("themeIndustrial")}</option>
                        <option value="high-contrast">{t("themeHighContrast")}</option>
                        <option value="emerald">{t("themeEmerald")}</option>
                        <option value="rose">{t("themeRose")}</option>
                        <option value="blue">{t("themeBlue")}</option>
                        <option value="amber">{t("themeAmber")}</option>
                        <option value="violet">{t("themeViolet")}</option>
                      </select>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
                      <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
                        {t("darkMode")}
                      </span>
                      <motion.button
                        whileHover={{ scale: 1.08 }}
                        whileTap={{ scale: 0.92 }}
                        type="button"
                        onClick={toggleTheme}
                        className="p-1.5 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-primary-500 transition-colors shadow-sm cursor-pointer"
                      >
                         {theme === 'dark' ? <Moon size={16} /> : <Sun size={16} />}
                      </motion.button>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
                      <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
                        {t("clickFeedbackTitle")}
                      </span>
                      <motion.button
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                        type="button"
                        onClick={() => setClickFeedbackEnabled(!clickFeedbackEnabled)}
                        className={`px-3 py-1.5 rounded-lg border text-[10px] font-mono font-bold uppercase transition-all cursor-pointer ${
                          clickFeedbackEnabled
                            ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                            : 'bg-white dark:bg-slate-950 text-slate-500 border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900'
                        }`}
                      >
                        {clickFeedbackEnabled ? t("statusOn") : t("statusOff")}
                      </motion.button>
                    </div>
                  </div>

                  <motion.div
                    whileHover={{ scale: 1.01 }}
                    className="flex items-center justify-between px-5 py-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl group transition-all hover:border-primary-500/30"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 bg-primary-100 dark:bg-primary-900/20 text-primary-500 rounded-lg">
                        <ShieldCheck size={16} />
                      </div>
                      <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest">
                        {t("changeRole")}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono font-bold text-primary-600 dark:text-primary-400 uppercase tracking-widest bg-white dark:bg-slate-950 px-3 py-1 border border-primary-200 dark:border-primary-800 rounded-lg shadow-sm">
                      {user.role}
                    </span>
                  </motion.div>

                  <div className="flex gap-4 pt-4">
                    <motion.button
                      whileHover={{
                        scale: 1.02,
                        backgroundColor: "rgba(241, 245, 249, 1)",
                      }}
                      whileTap={{ scale: 0.98 }}
                      type="button"
                      onClick={onClose}
                      className="flex-1 py-2.5 text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest hover:bg-slate-100 dark:hover:bg-slate-900 border border-slate-300 dark:border-slate-700 transition-all focus:outline-none rounded-xl"
                    >
                      {t("cancel")}
                    </motion.button>
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      type="submit"
                      disabled={isSaving}
                      className="flex-[2] py-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-mono font-bold text-[10px] uppercase tracking-widest shadow-xl disabled:opacity-70 flex items-center justify-center gap-2 focus:outline-none transition-all rounded-xl"
                    >
                      {isSaving ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <>
                          <Save size={16} />
                          {t("save")}
                        </>
                      )}
                    </motion.button>
                  </div>
                </form>

                  <div className="mt-2 mb-6 pt-6 border-t border-slate-200 dark:border-slate-800 text-center">
                    <p className="text-[9px] font-mono font-bold text-slate-400 uppercase tracking-widest">
                      {t("systemDesignedBy")}
                    </p>
                    <p className="text-[10px] font-mono font-bold text-slate-600 dark:text-slate-300 uppercase tracking-widest">
                      孙浩峻 (Sun Haojun)
                    </p>
                    <p className="text-[9px] font-mono text-slate-400 uppercase tracking-widest">
                      {t("priInstitute")}
                    </p>
                  </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
