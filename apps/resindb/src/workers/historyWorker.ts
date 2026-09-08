import { openDB, DBSchema, IDBPDatabase } from 'idb';
import { Product } from '@/types/index';
import { HistoryRecord } from '@/lib/adapters/types';

interface HistoryDB extends DBSchema {
  history: {
    key: string;
    value: HistoryRecord;
    indexes: {
      'by-timestamp': number;
    };
  };
}

let dbPromise: Promise<IDBPDatabase<HistoryDB>> | null = null;

async function getDB() {
  if (!dbPromise) {
    dbPromise = openDB<HistoryDB>('resin-history-db', 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('history')) {
          const store = db.createObjectStore('history', { keyPath: 'id' });
          store.createIndex('by-timestamp', 'timestamp');
        }
      },
    });
  }
  return dbPromise;
}

export type HistoryWorkerMessage = 
  | { type: 'PUSH_SNAPSHOT', payload: { description: string; snapshot: Product[] } }
  | { type: 'GET_HISTORY' }
  | { type: 'GET_SNAPSHOT', payload: { id: string } };

export type HistoryWorkerResponse = 
  | { type: 'HISTORY_UPDATED', payload: { history: Omit<HistoryRecord, 'snapshot'>[] } }
  | { type: 'SNAPSHOT_DATA', payload: { id: string; snapshot: Product[] } }
  | { type: 'ERROR', payload: { message: string } };

self.onmessage = async (e: MessageEvent<HistoryWorkerMessage>) => {
  try {
    const msg = e.data;
    const db = await getDB();

    if (msg.type === 'PUSH_SNAPSHOT') {
       const newRecord: HistoryRecord = {
          id: self.crypto.randomUUID ? self.crypto.randomUUID() : `hist-${Date.now()}`,
          timestamp: Date.now(),
          description: msg.payload.description,
          snapshot: msg.payload.snapshot, // Structured clone automatically done by postMessage
       };
       
       await db.put('history', newRecord);
       
       // Prune keeping only last 50
       const tx = db.transaction('history', 'readwrite');
       const store = tx.objectStore('history');
       const index = store.index('by-timestamp');
       let cursor = await index.openCursor(null, 'prev');
       let count = 0;
       while (cursor) {
          count++;
          if (count > 50) {
             await cursor.delete();
          }
          cursor = await cursor.continue();
       }
       await tx.done;

       // Broadcast updated history (without snapshot payload)
       const allRecords = await db.getAllFromIndex('history', 'by-timestamp');
       allRecords.reverse(); // Newest first
       const summary = allRecords.map(r => ({
           id: r.id,
           timestamp: r.timestamp,
           description: r.description
       })) as HistoryRecord[];
       
       self.postMessage({ type: 'HISTORY_UPDATED', payload: { history: summary } } as HistoryWorkerResponse);
    } 
    else if (msg.type === 'GET_HISTORY') {
       const allRecords = await db.getAllFromIndex('history', 'by-timestamp');
       allRecords.reverse();
       const summary = allRecords.map(r => ({
           id: r.id,
           timestamp: r.timestamp,
           description: r.description
       })) as HistoryRecord[];
       self.postMessage({ type: 'HISTORY_UPDATED', payload: { history: summary } } as HistoryWorkerResponse);
    }
    else if (msg.type === 'GET_SNAPSHOT') {
       const record = await db.get('history', msg.payload.id);
       if (record) {
           self.postMessage({ type: 'SNAPSHOT_DATA', payload: { id: record.id, snapshot: record.snapshot } } as HistoryWorkerResponse);
       } else {
           throw new Error('Snapshot not found');
       }
    }
  } catch (err) {
    self.postMessage({ type: 'ERROR', payload: { message: err instanceof Error ? err.message : 'Unknown error' } } as HistoryWorkerResponse);
  }
};
