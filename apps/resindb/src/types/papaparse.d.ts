declare module 'papaparse' {
  export interface ParseError {
    type: string;
    code: string;
    message: string;
    row?: number;
    index?: number;
  }

  export interface ParseMeta {
    delimiter: string;
    linebreak: string;
    aborted: boolean;
    fields?: string[];
    truncated: boolean;
    cursor: number;
  }

  export interface ParseResult<T> {
    data: T[];
    errors: ParseError[];
    meta: ParseMeta;
  }

  export interface ParseConfig<T> {
    header?: boolean;
    skipEmptyLines?: boolean | 'greedy';
    dynamicTyping?: boolean;
    complete?: (results: ParseResult<T>, file?: File) => void;
    error?: (error: Error, file?: File) => void;
  }

  interface PapaParseApi {
    parse<T = Record<string, unknown>>(input: string, config?: ParseConfig<T>): ParseResult<T>;
    parse<T = Record<string, unknown>>(input: File, config: ParseConfig<T>): void;
  }

  const Papa: PapaParseApi;
  export default Papa;
}
