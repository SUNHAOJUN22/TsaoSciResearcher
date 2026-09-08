import { createGzip } from 'node:zlib';
import { pipeline } from 'node:stream/promises';
import { createReadStream, createWriteStream } from 'node:fs';
import { mkdir, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..'); const dist=path.join(root,'dist'); const artifactDir=path.join(root,'artifacts'); const temp=path.join(artifactDir,'.gzip-metrics'); await mkdir(temp,{recursive:true});
async function walk(dir){const out=[];for(const entry of await readdir(dir,{withFileTypes:true})){const full=path.join(dir,entry.name);if(entry.isDirectory())out.push(...await walk(full));else out.push(full);}return out;}
const files=await walk(dist); const rows=[];
for(const file of files){const relative=path.relative(dist,file).replaceAll(path.sep,'/');const bytes=(await stat(file)).size;let gzipBytes=null;if(/\.(js|css|html|json|svg)$/.test(file)){const gz=path.join(temp,`${rows.length}.gz`);await pipeline(createReadStream(file),createGzip({level:9}),createWriteStream(gz));gzipBytes=(await stat(gz)).size;}rows.push({file:relative,bytes,gzipBytes});}
const html=await readFile(path.join(dist,'index.html'),'utf8'); const entryMatch=html.match(/<script[^>]+src="([^"]+\.js)"/); const modulePreloads=[...html.matchAll(/rel="modulepreload"[^>]+href="([^"]+\.js)"/g)].map(m=>m[1]);
const totalBytes=rows.reduce((s,r)=>s+r.bytes,0); const dataBytes=rows.filter(r=>r.file.startsWith('data/')).reduce((s,r)=>s+r.bytes,0); const largest=[...rows].sort((a,b)=>b.bytes-a.bytes).slice(0,16); const entryFile=(entryMatch?.[1]??'').replace(/^\//,''); const entry=rows.find(r=>r.file===entryFile); const echarts=rows.filter(r=>/echarts-core.*\.js$/.test(r.file)).sort((a,b)=>b.bytes-a.bytes)[0];
const budgets={entryGzipBytes:350000,echartsRawBytes:900000};
if(!entry||!Number.isFinite(entry.gzipBytes)) throw new Error('Unable to identify initial entry gzip size');
if(entry.gzipBytes>budgets.entryGzipBytes) throw new Error(`Initial entry gzip budget exceeded: ${entry.gzipBytes} > ${budgets.entryGzipBytes}`);
if(!echarts) throw new Error('Unable to identify modular ECharts chunk');
if(echarts.bytes>budgets.echartsRawBytes) throw new Error(`ECharts raw budget exceeded: ${echarts.bytes} > ${budgets.echartsRawBytes}`);
const report={schemaVersion:2,generatedAt:new Date().toISOString(),entryScript:entryMatch?.[1]??null,modulePreloads,fileCount:rows.length,totalBytes,externalResinDataBytes:dataBytes,budgets,entry,echarts,largestFiles:largest};
await mkdir(artifactDir,{recursive:true});await writeFile(path.join(artifactDir,'build-metrics.json'),`${JSON.stringify(report,null,2)}\n`);await rm(temp,{recursive:true,force:true});console.log(`Build metrics passed: entry ${entry.gzipBytes}/${budgets.entryGzipBytes} gzip bytes, ECharts ${echarts.bytes}/${budgets.echartsRawBytes} raw bytes, ${dataBytes} external data bytes.`);
