import { mkdir } from 'node:fs/promises';
import path from 'node:path';

await mkdir(path.resolve(import.meta.dirname, '..', 'artifacts'), { recursive: true });
