import React from 'react';
import { Globe, Moon, Sun, Sparkles, User as UserIcon, Shield } from 'lucide-react';
import { motion } from 'motion/react';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from '@/contexts/ThemeContext';
import { User as UserType } from '@/types/index';
import { UserAvatar } from '@/components/ui/UserAvatar';

interface AuthScreenProps {
  onLogin: (user: UserType) => void;
}

const DEMO_ACCOUNTS: UserType[] = [
  {
    id: 'demo-admin',
    name: 'Demo Admin',
    email: 'admin@example.invalid',
    role: 'admin',
  },
  {
    id: 'demo-editor',
    name: 'Demo Editor',
    email: 'editor@example.invalid',
    role: 'editor',
  },
  {
    id: 'demo-viewer',
    name: 'Demo Viewer',
    email: 'viewer@example.invalid',
    role: 'viewer',
  },
];

const PrecisionLabLogo: React.FC<{ className?: string }> = ({ className }) => (
  <motion.svg
    viewBox="0 0 100 100"
    className={className}
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    initial="initial"
    animate="animate"
  >
    <circle cx="50" cy="50" r="48" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 2" className="text-slate-200 dark:text-slate-800" />
    <motion.path
      d="M50 20 L80 40 L80 70 L50 90 L20 70 L20 40 Z"
      stroke="currentColor"
      strokeWidth="1.5"
      className="text-primary-500/50"
      initial={{ pathLength: 0 }}
      animate={{ pathLength: 1 }}
      transition={{ duration: 1.2, ease: 'easeInOut' }}
    />
    <motion.path
      d="M50 35 L65 45 L65 60 L50 70 L35 60 L35 45 Z"
      fill="currentColor"
      className="text-primary-600 dark:text-primary-400"
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 200, damping: 20, delay: 0.25 }}
    />
  </motion.svg>
);

export const AuthScreen: React.FC<AuthScreenProps> = ({ onLogin }) => {
  const { language, toggleLanguage, t } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const zh = language === 'zh';

  return (
    <div className="relative flex min-h-[100dvh] items-center justify-center overflow-hidden bg-slate-50 p-4 transition-colors duration-500 dark:bg-slate-950">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-[-10%] top-[-10%] h-[60%] w-[60%] rounded-full bg-primary-600/10 blur-[120px]" />
        <div className="absolute right-[-10%] top-[20%] h-[50%] w-[50%] rounded-full bg-sky-500/10 blur-[120px]" />
        <div className="absolute bottom-[-20%] left-[20%] h-[70%] w-[70%] rounded-full bg-indigo-500/10 blur-[120px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: 'easeOut' }}
        className="relative z-10 flex w-full max-w-md flex-col overflow-hidden rounded-[2.5rem] border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="h-1.5 bg-linear-to-r from-emerald-500 via-primary-500 to-indigo-500" />

        <div className="shrink-0 p-6 pb-4 text-center md:p-10 md:pb-6">
          <div className="mb-5 inline-flex rounded-[2rem] border border-slate-100 bg-white p-4 shadow-xl dark:border-slate-700 dark:bg-slate-800">
            <PrecisionLabLogo className="h-14 w-14" />
          </div>
          <h1 className="mb-3 text-3xl font-black tracking-tight text-slate-900 dark:text-white">
            {t('signInTitle')}
          </h1>
          <div className="flex items-center justify-center gap-2 text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
            <Sparkles size={14} className="text-amber-500" />
            ResinDB Pro
            <span className="h-1 w-1 rounded-full bg-slate-300 dark:bg-slate-700" />
            {zh ? '演示角色选择' : 'Demo role selection'}
          </div>
          <p className="mt-4 text-xs leading-5 text-slate-500 dark:text-slate-400">
            {zh
              ? '这些角色只用于前端功能演示，不执行真实身份认证，也不代表组织账号。'
              : 'These roles are for front-end demonstration only. They do not perform real authentication or represent organization accounts.'}
          </p>
        </div>

        <div className="space-y-3 px-6 pb-7 md:px-10 md:pb-10">
          <div className="mb-4 flex items-center gap-4 text-xs font-bold uppercase tracking-widest text-slate-400">
            <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
            {t('selectAccount')}
            <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
          </div>

          {DEMO_ACCOUNTS.map((account) => (
            <motion.button
              key={account.id}
              whileHover={{ scale: 1.015 }}
              whileTap={{ scale: 0.985 }}
              onClick={() => onLogin(account)}
              className="group flex w-full items-center gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-left transition-all hover:border-primary-300 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800/50 dark:hover:border-primary-700 dark:hover:bg-slate-800"
            >
              <UserAvatar name={account.name} className="h-10 w-10 shrink-0 rounded-full text-xs" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-bold text-slate-900 transition-colors group-hover:text-primary-600 dark:text-white dark:group-hover:text-primary-400">
                  {account.name}
                </div>
                <div className="truncate text-xs text-slate-500 dark:text-slate-400">{account.email}</div>
              </div>
              <div className="shrink-0 rounded-xl border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-900">
                {account.role === 'admin' && <Shield size={16} className="text-rose-500" />}
                {account.role === 'editor' && <Sparkles size={16} className="text-emerald-500" />}
                {account.role === 'viewer' && <UserIcon size={16} className="text-slate-400" />}
              </div>
            </motion.button>
          ))}
        </div>

        <div className="relative flex shrink-0 justify-center gap-6 border-t border-slate-100 bg-slate-50/50 p-5 dark:border-slate-800 dark:bg-slate-950/30">
          <motion.button
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.92 }}
            onClick={toggleLanguage}
            className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 transition-all dark:text-slate-400"
          >
            <Globe size={14} strokeWidth={2.5} /> {language === 'zh' ? 'English' : '中文'}
          </motion.button>
          <span className="mt-1 h-3 w-px bg-slate-200 dark:bg-slate-800" />
          <motion.button
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.92 }}
            onClick={toggleTheme}
            className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 transition-all dark:text-slate-400"
          >
            {theme === 'dark' ? <Sun size={14} strokeWidth={2.5} /> : <Moon size={14} strokeWidth={2.5} />}
            {theme === 'dark' ? 'Light' : 'Dark'}
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
};
