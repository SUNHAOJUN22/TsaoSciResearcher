import { APP_VERSION } from '@/config/version';
import React, { useMemo, useState } from 'react';
import { Download, MessageSquare, X } from 'lucide-react';
import { safeStorage } from '@/lib/utils';

interface FeedbackModalProps { isOpen: boolean; onClose: () => void }
type FeedbackType='bug'|'feature'|'data'|'other';
type Severity='low'|'medium'|'high'|'critical';
const STORAGE_KEY='resindb-feedback-queue';
export const redactFeedbackText=(value:string)=>value
  .replace(/(api[_ -]?key|token|password|secret)\s*[:=]\s*[^\s,;]+/gi,'$1=[REDACTED]')
  .replace(/\b(sk-[A-Za-z0-9_-]{8,})\b/g,'[REDACTED_KEY]');
export interface FeedbackRecord { id:string; createdAt:string; type:FeedbackType; severity:Severity; module:string; title:string; description:string; steps:string; environment:{version:string;url:string;language:string;theme:string;userAgent:string}; privacy:string }
export const buildFeedbackRecord=(input:Omit<FeedbackRecord,'id'|'createdAt'|'environment'|'privacy'>):FeedbackRecord=>({
  ...input,title:redactFeedbackText(input.title.trim()),description:redactFeedbackText(input.description.trim()),steps:redactFeedbackText(input.steps.trim()),
  id:`feedback-${Date.now()}-${Math.random().toString(36).slice(2,8)}`,createdAt:new Date().toISOString(),
  environment:{version:APP_VERSION,url:location.pathname,language:document.documentElement.lang||'unknown',theme:document.documentElement.classList.contains('dark')?'dark':'light',userAgent:navigator.userAgent},
  privacy:'No API keys, passwords or complete resin database records are intentionally collected.',
});
const readQueue=():FeedbackRecord[]=>{try{return JSON.parse(safeStorage.local.getItem(STORAGE_KEY)||'[]') as FeedbackRecord[];}catch{return[];}};
export const FeedbackModal:React.FC<FeedbackModalProps>=({isOpen,onClose})=>{
  const [type,setType]=useState<FeedbackType>('bug');const[severity,setSeverity]=useState<Severity>('medium');const[module,setModule]=useState('dashboard');
  const[title,setTitle]=useState('');const[description,setDescription]=useState('');const[steps,setSteps]=useState('');const[status,setStatus]=useState('');
  const valid=useMemo(()=>title.trim().length>=3&&description.trim().length>=10,[title,description]);
  if(!isOpen)return null;
  const save=(download:boolean)=>{if(!valid){setStatus('请填写标题和至少 10 个字符的描述。');return;}const record=buildFeedbackRecord({type,severity,module,title,description,steps});safeStorage.local.setItem(STORAGE_KEY,JSON.stringify([...readQueue(),record]));if(download){const blob=new Blob([JSON.stringify(record,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`resindb-feedback-${record.id}.json`;a.click();URL.revokeObjectURL(url);}setStatus(download?'反馈 JSON 已下载，并保存到本地待处理队列。':'反馈已保存到本地待处理队列。');};
  return <div className="fixed inset-0 z-[230] flex items-center justify-center bg-slate-950/50 p-4" data-testid="feedback-modal"><div className="w-full max-w-xl rounded-2xl border bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-950">
    <div className="mb-4 flex items-center justify-between"><div className="flex items-center gap-2"><MessageSquare size={18}/><h2 className="font-bold">反馈与诊断导出</h2></div><button type="button" onClick={onClose} aria-label="关闭反馈"><X size={18}/></button></div>
    <p className="mb-4 text-xs text-slate-500">当前版本没有反馈服务器。记录会保存在本浏览器，并可导出 JSON 交给维护人员；疑似密钥和密码会被自动脱敏。</p>
    <div className="grid gap-3 sm:grid-cols-3"><label className="text-xs">类型<select value={type} onChange={e=>setType(e.target.value as FeedbackType)} className="mt-1 w-full rounded-lg border p-2"><option value="bug">缺陷</option><option value="feature">建议</option><option value="data">数据问题</option><option value="other">其他</option></select></label><label className="text-xs">严重度<select value={severity} onChange={e=>setSeverity(e.target.value as Severity)} className="mt-1 w-full rounded-lg border p-2"><option value="low">低</option><option value="medium">中</option><option value="high">高</option><option value="critical">严重</option></select></label><label className="text-xs">模块<select value={module} onChange={e=>setModule(e.target.value)} className="mt-1 w-full rounded-lg border p-2"><option>dashboard</option><option>analytics</option><option>data-quality</option><option>dependency-map</option><option>pivot</option><option>beta-sandbox</option><option>import-export</option></select></label></div>
    <label className="mt-3 block text-xs">标题<input data-testid="feedback-title" value={title} onChange={e=>setTitle(e.target.value)} maxLength={120} className="mt-1 w-full rounded-lg border p-2"/></label>
    <label className="mt-3 block text-xs">描述<textarea data-testid="feedback-description" value={description} onChange={e=>setDescription(e.target.value)} maxLength={4000} className="mt-1 h-28 w-full rounded-lg border p-2"/></label>
    <label className="mt-3 block text-xs">复现步骤<textarea value={steps} onChange={e=>setSteps(e.target.value)} maxLength={3000} className="mt-1 h-20 w-full rounded-lg border p-2"/></label>
    <div aria-live="polite" className="mt-3 min-h-5 text-xs text-emerald-600">{status}</div><div className="mt-3 flex justify-end gap-2"><button type="button" onClick={()=>save(false)} className="rounded-lg border px-4 py-2 text-xs">保存本地</button><button data-testid="feedback-export" type="button" onClick={()=>save(true)} className="flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-xs text-white"><Download size={14}/>导出 JSON</button></div>
  </div></div>;
};
