import { describe, expect, it, vi } from 'vitest';
import type { Product, FormulaConfig } from '@/types/index';

type Loader=()=>Promise<unknown>;
const loaders:Record<string,Loader>={
  arrhenius:()=>import('@/workers/arrheniusWorker'),carreau:()=>import('@/workers/carreauWorker'),copula:()=>import('@/workers/copulaWorker'),
  dataQuality:()=>import('@/workers/dataQualityWorker'),featureImportance:()=>import('@/workers/featureImportanceWorker'),forecasting:()=>import('@/workers/forecastingWorker'),
  kde:()=>import('@/workers/kdeWorker'),kinetics:()=>import('@/workers/kineticsWorker'),kmeans:()=>import('@/workers/kmeansWorker'),mahalanobis:()=>import('@/workers/mahalanobisWorker'),
  monteCarlo:()=>import('@/workers/monteCarloWorker'),moo:()=>import('@/workers/mooWorker'),pareto:()=>import('@/workers/paretoWorker'),prony:()=>import('@/workers/pronyWorker'),
  rsm:()=>import('@/workers/rsmWorker'),similarity:()=>import('@/workers/similarityWorker'),sobol:()=>import('@/workers/sobolWorker'),spc:()=>import('@/workers/spcWorker'),
  spearman:()=>import('@/workers/spearmanWorker'),weibull:()=>import('@/workers/weibullWorker'),wlf:()=>import('@/workers/wlfWorker'),
};
const product=(id:string,a:number,b:number):Product=>({id,gradeName:`Grade ${id}`,manufacturerId:'m',manufacturer:'Demo',categoryIds:['cat_pp'],createdAt:'2025-01-01',updatedAt:'2026-01-01',properties:{A:{value:a},B:{value:b},密度:{value:0.9+a/100},弯曲模量:{value:1000+b*10}}});
const products=[1,2,3,4,5,6].map((n)=>product(String(n),n,n*n+1));
const formula:FormulaConfig={id:'f',name:'Score',expression:"Props['A'] + Props['B']",unit:'-'};
const messages:Record<string,unknown>={
  arrhenius:{type:'CALCULATE_ARRHENIUS',payload:{points:[{tempC:80,time:120},{tempC:100,time:60},{tempC:120,time:30}]}},
  carreau:{type:'FIT_CARREAU',payload:{shearRates:[0.1,1,10,100,1000],viscosities:[5000,3000,1000,300,100]}},
  copula:{type:'CALCULATE_COPULA',payload:{data:[{x:1,y:2},{x:2,y:2.5},{x:3,y:4},{x:4,y:5},{x:5,y:6.5}],gridSize:8}},
  dataQuality:{type:'RUN_MONITOR',payload:{allProducts:products}},
  featureImportance:{type:'CALCULATE_IMPORTANCE',payload:{featureNames:['x1','x2'],data:[[1,2,4],[2,1,5],[3,4,10],[4,2,9],[5,6,16],[6,3,14]]}},
  forecasting:{type:'RUN_FORECAST',payload:{products,propertyKey:'弯曲模量',algorithm:'linear',condition:'thermal',stressFactor:80}},
  kde:{type:'CALCULATE_KDE',payload:{points:[{x:1,y:1},{x:2,y:3},{x:3,y:2},{x:4,y:5}],gridSize:8}},
  kinetics:{type:'RUN_KINETICS',payload:{data:[{beta:5,tp:120},{beta:10,tp:130},{beta:20,tp:141},{beta:30,tp:148}],isoTemp:100}},
  kmeans:{type:'COMPUTE_KMEANS',payload:{data:products.map((p,i)=>({id:p.id,values:{a:i+1,b:(i+1)**2}})),keys:['a','b'],maxK:3}},
  mahalanobis:{type:'CALCULATE_MAHALANOBIS',payload:{data:products.map((p,i)=>({_id:p.id,name:p.gradeName,a:i+1,b:(i+1)**2+(i%2)})),features:['a','b'],alpha:0.05}},
  monteCarlo:{type:'RUN_SIMULATION',payload:{targetFormulaId:'f',formulas:[formula],product:products[1],variances:{A:5,B:5},iterations:100}},
  moo:{type:'RUN_MOO',payload:{data:[{x:1,y:2,z:5},{x:2,y:1,z:6},{x:3,y:4,z:9},{x:4,y:3,z:10},{x:5,y:5,z:12}],features:['x','y'],targets:[{name:'z',maximize:true},{name:'y',maximize:false}],iterations:12}},
  pareto:{type:'COMPUTE_PARETO',payload:{data:products.map((p,i)=>({id:p.id,values:{a:i+1,b:7-i}})),objectives:[{key:'a',minimize:true},{key:'b',minimize:true}]}},
  prony:{type:'RUN_PRONY',payload:{data:[{omega:0.1,storage:100,loss:20},{omega:1,storage:150,loss:35},{omega:10,storage:220,loss:50},{omega:100,storage:300,loss:45}],numTerms:2}},
  rsm:{type:'CALCULATE_RSM',payload:{data:[-1,0,1].flatMap(x1=>[-1,0,1].map(x2=>({x1,x2,y:10+2*x1-3*x2+x1*x1+0.5*x2*x2+x1*x2})))}},
  similarity:{type:'CALCULATE_SIMILARITY',payload:{products,features:['A','B'],threshold:0.1}},
  sobol:{type:'RUN_SOBOL',payload:{targetFormulaId:'f',formulas:[formula],product:products[2],variances:{A:5,B:5},iterations:80}},
  spc:{type:'CALCULATE_SPC',payload:{data:[9.8,10,10.1,9.9,10.2,10.05,9.95],usl:11,lsl:9}},
  spearman:{type:'COMPUTE_SPEARMAN',payload:{data:products.map((p,i)=>({id:p.id,values:{a:i+1,b:(i+1)**2}})),keys:['a','b']}},
  weibull:{type:'CALCULATE_WEIBULL',payload:{data:[20,22,25,27,30,35,40]}},
  wlf:{type:'CALCULATE_WLF',payload:{curves:[{temp:20,points:[{rate:0.1,visc:1000},{rate:1,visc:500},{rate:10,visc:200}]},{temp:40,points:[{rate:0.2,visc:800},{rate:2,visc:400},{rate:20,visc:160}]},{temp:60,points:[{rate:0.4,visc:650},{rate:4,visc:320},{rate:40,visc:130}]}],refTemp:40}},
};
function assertFinite(value:unknown,path='root'):void{if(typeof value==='number'){expect(Number.isFinite(value),path).toBe(true);}else if(Array.isArray(value)){value.forEach((v,i)=>assertFinite(v,`${path}[${i}]`));}else if(value&&typeof value==='object'){Object.entries(value).forEach(([k,v])=>assertFinite(v,`${path}.${k}`));}}
async function runWorker(name:string){vi.resetModules();const replies:unknown[]=[];const workerScope:{onmessage?: (event:MessageEvent)=>void;postMessage:(value:unknown)=>void}={postMessage:(value)=>replies.push(value)};vi.stubGlobal('self',workerScope);await loaders[name]();expect(workerScope.onmessage,`${name} handler`).toBeTypeOf('function');workerScope.onmessage!({data:messages[name]} as MessageEvent);await new Promise(r=>setTimeout(r,0));expect(replies.length,`${name} response`).toBeGreaterThan(0);const response=replies.at(-1) as {type?:string;error?:string;payload?:unknown};expect(response.type,`${name}: ${response.error??''}`).not.toBe('ERROR');assertFinite(response.payload,name);vi.unstubAllGlobals();}

describe('numerical worker matrix',()=>{for(const name of Object.keys(messages)){it(`${name} returns finite analysis output`,async()=>runWorker(name),20_000);}});
