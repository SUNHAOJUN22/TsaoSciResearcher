import { IndexedDBProductAdapter } from "@/lib/adapters/IndexedDBProductAdapter";
import { RemoteAPIProductAdapter } from "@/lib/adapters/RemoteAPIProductAdapter";
import { IProductAdapter } from "@/lib/adapters/types";

// 从环境变量读取适配器选择：可设为 'indexeddb' 或 'remote_api' (连接 MongoDB/MySQL 等后台)
const adapterType = import.meta.env.VITE_DATABASE_ADAPTER_TYPE || 'indexeddb';

const adapter: IProductAdapter = adapterType === 'remote_api' 
  ? new RemoteAPIProductAdapter() 
  : new IndexedDBProductAdapter();

export default adapter;
export * from "@/lib/adapters/types";
