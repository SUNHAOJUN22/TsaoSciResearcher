import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  Brain,
  Eraser,
  ImagePlus,
  Loader2,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Product, ProductUpdates } from '@/types/index';
import { useLanguage } from '@/contexts/LanguageContext';
import { AiApiSettingsModal } from '@/components/modals/AiApiSettingsModal';
import { getAiInsights, isAiConfigured } from '@/services/aiService';
import { generateId } from '@/lib/utils';

interface AiCopilotProps {
  data: Product[];
  activeChart?: string;
  actions: {
    handleDelete: (ids: string[]) => void;
    handleUpdate: (product: Product) => void;
    handleBatchUpdate: (ids: string[], updates: ProductUpdates) => void;
    handleImportData: (data: Product[]) => void;
  };
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

const MAX_IMAGE_BYTES = 4 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp']);

function createMessageId(): string {
  return `msg-${generateId()}`;
}

async function readImage(file: File): Promise<{ data: string; mimeType: string }> {
  if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
    throw new Error('Only PNG, JPEG, and WebP images are supported.');
  }
  if (file.size > MAX_IMAGE_BYTES) {
    throw new Error('Image size must not exceed 4 MB.');
  }

  const result = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Unable to read the selected image.'));
    reader.readAsDataURL(file);
  });
  const commaIndex = result.indexOf(',');
  if (commaIndex < 0) throw new Error('Invalid image data.');
  return { data: result.slice(commaIndex + 1), mimeType: file.type };
}

export const AiCopilot: React.FC<AiCopilotProps> = React.memo(({ data, activeChart }) => {
  const { language } = useLanguage();
  const zh = language === 'zh';
  const [open, setOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [configured, setConfigured] = useState(() => isAiConfigured());
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [deepAnalysis, setDeepAnalysis] = useState(false);
  const [image, setImage] = useState<{ name: string; data: string; mimeType: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const sampleCount = data.length;
  const contextLabel = useMemo(
    () => (activeChart ? `${activeChart}; ${sampleCount} records` : `${sampleCount} records`),
    [activeChart, sampleCount],
  );

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, loading]);

  const submit = async () => {
    const trimmed = query.trim();
    if ((!trimmed && !image) || loading) return;
    if (!configured) {
      setError(zh ? '请先配置 AI API Endpoint 和模型标识。' : 'Configure the AI API endpoint and model first.');
      setSettingsOpen(true);
      return;
    }

    const userText = trimmed || (zh ? '分析所附图片。' : 'Analyze the attached image.');
    setMessages((current) => [...current, { id: createMessageId(), role: 'user', content: userText }]);
    setQuery('');
    setError(null);
    setLoading(true);

    try {
      const answer = await getAiInsights(data, {
        query: `${userText}\n\nApplication context: ${contextLabel}`,
        isDeepThinking: deepAnalysis,
        imagePart: image ? { inlineData: { data: image.data, mimeType: image.mimeType } } : undefined,
      });
      setMessages((current) => [...current, { id: createMessageId(), role: 'assistant', content: answer }]);
      setImage(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'AI request failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleImageSelection = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(null);
    try {
      const parsed = await readImage(file);
      setImage({ name: file.name, ...parsed });
    } catch (imageError) {
      setImage(null);
      setError(imageError instanceof Error ? imageError.message : 'Unable to attach image.');
      event.target.value = '';
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={zh ? '打开 AI 助手' : 'Open AI assistant'}
        className="fixed bottom-20 right-5 z-40 inline-flex h-12 items-center gap-2 rounded-2xl bg-slate-900 px-4 text-sm font-bold text-white shadow-xl transition hover:-translate-y-0.5 hover:bg-slate-800 dark:bg-white dark:text-slate-900 md:bottom-6"
      >
        <Sparkles size={17} />
        <span className="hidden sm:inline">AI</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.aside
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            className="fixed inset-y-0 right-0 z-[100] flex w-full max-w-xl flex-col border-l border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-950"
            aria-label={zh ? 'AI 材料分析助手' : 'AI materials assistant'}
          >
            <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-indigo-500/10 p-2 text-indigo-600 dark:text-indigo-400"><Brain size={19} /></div>
                <div>
                  <h2 className="font-bold text-slate-900 dark:text-white">{zh ? 'AI 数据解读' : 'AI Data Review'}</h2>
                  <p className="text-xs text-slate-500">{contextLabel}</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button type="button" onClick={() => setSettingsOpen(true)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-900" aria-label="API settings"><Settings size={18} /></button>
                <button type="button" onClick={() => setOpen(false)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-900" aria-label="Close"><X size={18} /></button>
              </div>
            </header>

            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 text-xs dark:border-slate-800">
              <span className={`inline-flex items-center gap-1.5 font-semibold ${configured ? 'text-emerald-600' : 'text-amber-600'}`}>
                <ShieldCheck size={15} />
                {configured ? (zh ? 'API 已配置' : 'API configured') : (zh ? 'API 未配置' : 'API not configured')}
              </span>
              <label className="inline-flex cursor-pointer items-center gap-2 text-slate-600 dark:text-slate-300">
                <input type="checkbox" checked={deepAnalysis} onChange={(event) => setDeepAnalysis(event.target.checked)} />
                {zh ? '低温度严谨分析' : 'Low-temperature analysis'}
              </label>
            </div>

            <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
              {messages.length === 0 && (
                <div className="rounded-2xl border border-dashed border-slate-300 p-5 text-sm leading-6 text-slate-600 dark:border-slate-700 dark:text-slate-300">
                  {zh
                    ? '助手只会分析当前界面的有限数据和你提供的图片，不会伪造实验、执行外部仿真或自动修改数据库。'
                    : 'The assistant analyzes only the limited records and images supplied by this interface. It does not fabricate experiments, run external simulations, or modify the database automatically.'}
                </div>
              )}
              {messages.map((message) => (
                <article key={message.id} className={`rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'ml-10 bg-indigo-600 text-white' : 'mr-6 bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-100'}`}>
                  {message.role === 'assistant' ? <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown> : message.content}
                </article>
              ))}
              {loading && <div className="inline-flex items-center gap-2 rounded-xl bg-slate-100 px-4 py-3 text-sm text-slate-600 dark:bg-slate-900 dark:text-slate-300"><Loader2 className="animate-spin" size={16} />{zh ? '正在分析…' : 'Analyzing…'}</div>}
              {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300">{error}</div>}
            </div>

            <footer className="border-t border-slate-200 p-4 dark:border-slate-800">
              {image && (
                <div className="mb-3 flex items-center justify-between rounded-xl bg-slate-100 px-3 py-2 text-xs text-slate-700 dark:bg-slate-900 dark:text-slate-200">
                  <span className="truncate">{image.name}</span>
                  <button type="button" onClick={() => setImage(null)} className="ml-3 text-rose-500"><X size={15} /></button>
                </div>
              )}
              <div className="flex items-end gap-2">
                <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleImageSelection} />
                <button type="button" onClick={() => fileInputRef.current?.click()} className="rounded-xl border border-slate-200 p-3 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-900" aria-label="Attach image"><ImagePlus size={18} /></button>
                <textarea
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault();
                      void submit();
                    }
                  }}
                  rows={2}
                  maxLength={4000}
                  placeholder={zh ? '询问当前数据；Enter 发送，Shift+Enter 换行' : 'Ask about current data; Enter to send'}
                  className="min-h-[48px] flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-indigo-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
                <button type="button" onClick={() => void submit()} disabled={loading || (!query.trim() && !image)} className="rounded-xl bg-indigo-600 p-3 text-white disabled:cursor-not-allowed disabled:opacity-40" aria-label="Send"><Send size={18} /></button>
              </div>
              {messages.length > 0 && (
                <button type="button" onClick={() => { setMessages([]); setError(null); }} className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-rose-600"><Eraser size={14} />{zh ? '清空会话' : 'Clear conversation'}</button>
              )}
            </footer>
          </motion.aside>
        )}
      </AnimatePresence>

      <AiApiSettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={() => setConfigured(isAiConfigured())}
      />
    </>
  );
});

AiCopilot.displayName = 'AiCopilot';
