type LogLevel = "info" | "warn" | "error" | "debug";

class Logger {
  private isDev = import.meta.env.DEV;

  private log(level: LogLevel, ...args: unknown[]) {
    const timestamp = new Date().toISOString();
    const style = {
      info: "color: #3b82f6; font-weight: bold;",
      warn: "color: #f59e0b; font-weight: bold;",
      error: "color: #ef4444; font-weight: bold;",
      debug: "color: #8b5cf6; font-weight: bold;",
    };

    if (this.isDev || level === "error") {
      console.log(
        `%c[${level.toUpperCase()}] %c[${timestamp}]`,
        style[level],
        "color: gray; font-size: 10px;",
        ...args,
      );
    }

    // In production, we could send logs to an external service here
  }

  info(...args: unknown[]) {
    this.log("info", ...args);
  }
  warn(...args: unknown[]) {
    this.log("warn", ...args);
  }
  error(...args: unknown[]) {
    this.log("error", ...args);
  }
  debug(...args: unknown[]) {
    this.log("debug", ...args);
  }
}

export const logger = new Logger();
