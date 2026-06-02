import { spawn, ChildProcess, execFile } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as crypto from 'crypto';
import {
  buildDatabaseUrl,
  buildPythonImportPath,
  getEmbeddedPlaywrightNodeDir,
  prependPathEntries,
} from './desktop-config';

const CREATE_NO_WINDOW = 0x08000000;

export interface ProcessConfig {
  pgDir: string;
  pgData: string;
  pythonCommand?: string;
  pythonDir?: string;
  backendDir: string;
  mediacrawlerDir: string;
  apisDir: string;
  xhsUtilsDir: string;
  staticDir: string;
  frontendDir: string;
  port: number;
  pgPort: number;
  isDev: boolean;
}

export class ProcessManager {
  private config: ProcessConfig;
  private processes: Map<string, ChildProcess> = new Map();
  private safePathCache: Map<string, string> = new Map();

  constructor(config: ProcessConfig) {
    this.config = config;
  }

  private getSafePath(originalPath: string): string {
    if (process.platform !== 'win32') return originalPath;
    if (/^[\x00-\x7F]*$/.test(originalPath)) return originalPath;

    const cached = this.safePathCache.get(originalPath);
    if (cached) {
      try {
        fs.accessSync(cached);
        return cached;
      } catch {
        this.safePathCache.delete(originalPath);
      }
    }

    const junctionBase = path.join(
      process.env.LOCALAPPDATA || process.env.TEMP || 'C:\\Temp',
      'loan-radar-links'
    );
    const hash = crypto.createHash('md5').update(originalPath).digest('hex').slice(0, 8);
    const junctionPath = path.join(junctionBase, `link_${hash}`);

    try {
      if (fs.existsSync(junctionPath)) {
        fs.rmdirSync(junctionPath);
      }
      fs.mkdirSync(junctionBase, { recursive: true });
      fs.symlinkSync(originalPath, junctionPath, 'junction');
      this.safePathCache.set(originalPath, junctionPath);
      console.log(`[ProcessManager] Junction: ${junctionPath} -> ${originalPath}`);
      return junctionPath;
    } catch (err) {
      console.error(`[ProcessManager] Failed to create junction for ${originalPath}: ${err}`);
      return originalPath;
    }
  }

  private getPythonPath(): string {
    if (this.config.pythonDir) {
      return path.join(this.config.pythonDir, 'python.exe');
    }
    if (this.config.pythonCommand) {
      return this.config.pythonCommand;
    }
    return 'python';
  }

  private getPythonwPath(): string {
    if (this.config.pythonDir) {
      const pythonw = path.join(this.config.pythonDir, 'pythonw.exe');
      if (fs.existsSync(pythonw)) {
        return pythonw;
      }
      return path.join(this.config.pythonDir, 'python.exe');
    }
    return 'pythonw';
  }

  private shouldUseShell(): boolean {
    return this.config.isDev && !this.config.pythonDir;
  }

  private getLogDir(): string {
    const logDir = path.join(
      process.env.LOCALAPPDATA || process.env.TEMP || 'C:\\Temp',
      'loan-radar-logs'
    );
    fs.mkdirSync(logDir, { recursive: true });
    return logDir;
  }

  private getEnv(): NodeJS.ProcessEnv {
    const env: NodeJS.ProcessEnv = { ...process.env };
    const safePgDir = this.getSafePath(this.config.pgDir);
    const pythonImportPath = this.getPythonImportPath();
    const pathEntries: string[] = [];

    if (this.config.pythonDir) {
      const embeddedNodeDir = getEmbeddedPlaywrightNodeDir(this.config.pythonDir);
      pathEntries.push(this.config.pythonDir, path.join(this.config.pythonDir, 'Scripts'));
      if (fs.existsSync(path.join(embeddedNodeDir, 'node.exe'))) {
        pathEntries.unshift(embeddedNodeDir);
        env.EXECJS_RUNTIME = 'Node';
      }
    }
    if (fs.existsSync(this.config.pgDir)) {
      pathEntries.push(path.join(safePgDir, 'bin'));
    }

    const ffmpegDir = path.join(path.dirname(this.config.pgDir), 'ffmpeg');
    if (fs.existsSync(path.join(ffmpegDir, 'ffmpeg.exe'))) {
      pathEntries.push(ffmpegDir);
    }

    env.PATH = prependPathEntries(env.PATH, pathEntries);

    env.MEDIA_CRAWLER_HOME = this.config.mediacrawlerDir;
    env.FRONTEND_SERVE_STATIC = 'true';
    env.FRONTEND_BUILD_DIR = this.config.frontendDir;
    env.DATABASE_URL = buildDatabaseUrl(this.config.pgPort);
    env.LOAN_RADAR_PYTHONPATH = pythonImportPath;
    env.PYTHONPATH = pythonImportPath;
    env.PYTHONIOENCODING = 'utf-8';
    env.STATIC_DIR = this.config.staticDir;

    const toolsDir = path.dirname(this.config.pgDir);
    if (fs.existsSync(toolsDir)) {
      env.LOAN_RADAR_TOOLS_DIR = toolsDir;
    }

    return env;
  }

  private getPythonImportPath(): string {
    return buildPythonImportPath([
      this.config.backendDir,
      this.config.mediacrawlerDir,
      path.dirname(this.config.apisDir),
      this.config.apisDir,
      this.config.xhsUtilsDir,
    ]);
  }

  private getPythonModuleArgs(moduleName: string, moduleArgs: string[]): string[] {
    const bootstrap = [
      'import os, runpy, sys',
      'paths = [p for p in os.environ.get("LOAN_RADAR_PYTHONPATH", "").split(os.pathsep) if p]',
      'sys.path[:0] = [p for p in paths if p not in sys.path]',
      'sys.argv = [sys.argv[1]] + sys.argv[2:]',
      'runpy.run_module(sys.argv[0], run_name="__main__", alter_sys=True)',
    ].join('; ');
    return ['-c', bootstrap, moduleName, ...moduleArgs];
  }

  private spawnHidden(command: string, args: string[], options: any): ChildProcess {
    const opts: any = {
      ...options,
      windowsHide: true,
    };
    if (process.platform === 'win32') {
      opts.creationFlags = CREATE_NO_WINDOW;
      delete opts.detached;
    }
    return spawn(command, args, opts);
  }

  private configurePostgreSQLDataDir(pgData: string): void {
    const pgHba = path.join(pgData, 'pg_hba.conf');
    if (fs.existsSync(pgHba)) {
      try {
        let content = fs.readFileSync(pgHba, 'utf-8');
        content = content.replace(/^host\s+.*$/gm, '');
        content = content.replace(/^local\s+.*$/gm, '');
        content = content.trim() + '\n';
        content += 'local   all   all   trust\n';
        content += 'host    all   all   127.0.0.1/32   trust\n';
        content += 'host    all   all   ::1/128   trust\n';
        fs.writeFileSync(pgHba, content, 'utf-8');
        console.log('[PostgreSQL] pg_hba.conf configured for TCP/IP access');
      } catch (err) {
        console.warn('[PostgreSQL] Failed to update pg_hba.conf:', err);
      }
    }

    const pgConf = path.join(pgData, 'postgresql.conf');
    if (fs.existsSync(pgConf)) {
      try {
        let content = fs.readFileSync(pgConf, 'utf-8');
        content = content.replace(/^#?listen_addresses\s*=.*$/m, "listen_addresses = '127.0.0.1'");
        content = content.replace(/^#?port\s*=.*$/m, `port = ${this.config.pgPort}`);
        if (!content.includes('listen_addresses')) {
          content += "\nlisten_addresses = '127.0.0.1'\n";
        }
        if (!/^port\s*=/m.test(content)) {
          content += `\nport = ${this.config.pgPort}\n`;
        }
        fs.writeFileSync(pgConf, content, 'utf-8');
        console.log(`[PostgreSQL] postgresql.conf configured on port ${this.config.pgPort}`);
      } catch (err) {
        console.warn('[PostgreSQL] Failed to update postgresql.conf:', err);
      }
    }
  }

  async initPostgreSQL(pgData: string): Promise<void> {
    if (fs.existsSync(path.join(pgData, 'PG_VERSION'))) {
      this.configurePostgreSQLDataDir(pgData);
      return;
    }

    if (fs.existsSync(pgData)) {
      const files = fs.readdirSync(pgData);
      if (files.length > 0) {
        for (const file of files) {
          const filePath = path.join(pgData, file);
          try {
            fs.rmSync(filePath, { recursive: true, force: true });
          } catch {}
        }
      }
    } else {
      fs.mkdirSync(pgData, { recursive: true });
    }

    const safePgDir = this.getSafePath(this.config.pgDir);
    const safePgData = this.getSafePath(pgData);
    const initdb = path.join(safePgDir, 'bin', 'initdb.exe');
    if (!fs.existsSync(initdb)) {
      throw new Error(`PostgreSQL initdb not found: ${initdb}`);
    }

    return new Promise<void>((resolve, reject) => {
      const proc = this.spawnHidden(initdb, [
        '-U', 'postgres',
        '-A', 'trust',
        '-D', safePgData,
        '--encoding=UTF8',
        '--locale=C',
      ], { stdio: 'pipe' });

      let stderr = '';
      proc.stderr?.on('data', (d: Buffer) => { stderr += d.toString(); });

      proc.on('close', (code) => {
        if (code === 0) {
          this.configurePostgreSQLDataDir(pgData);
          resolve();
        } else {
          reject(new Error(`initdb failed (code ${code}): ${stderr}`));
        }
      });

      proc.on('error', reject);
    });
  }

  async installDependencies(): Promise<void> {
    if (!this.config.isDev) {
      return;
    }
    const python = this.getPythonPath();
    const env = this.getEnv();

    const runPip = (cwd: string, args: string[]): Promise<void> => {
      return new Promise<void>((resolve, reject) => {
        const proc = this.spawnHidden(python, ['-m', 'pip', ...args], {
          cwd, env, stdio: 'pipe', shell: this.shouldUseShell(),
        });
        proc.on('close', (code) => code === 0 ? resolve() : reject(new Error(`pip ${args.join(' ')} failed (code ${code})`)));
        proc.on('error', reject);
      });
    };

    await runPip(this.config.backendDir, ['install', '-r', 'requirements.txt', '-q']);
    await runPip(this.config.mediacrawlerDir, ['install', '-e', '.', '-q']).catch(() => {});
  }

  async runMigrations(): Promise<void> {
    const python = this.getPythonPath();
    const env = this.getEnv();

    return new Promise<void>((resolve, reject) => {
      const proc = this.spawnHidden(python, this.getPythonModuleArgs('alembic', ['upgrade', 'head']), {
        cwd: this.config.backendDir,
        env,
        stdio: 'pipe',
        shell: this.shouldUseShell(),
      });

      let stdout = '';
      let stderr = '';
      proc.stdout?.on('data', (d: Buffer) => { stdout += d.toString(); });
      proc.stderr?.on('data', (d: Buffer) => { stderr += d.toString(); });

      proc.on('close', (code) => {
        if (code === 0) {
          console.log('[Alembic] Migration completed successfully');
          resolve();
        } else {
          const errMsg = stderr || stdout || `exit code ${code}`;
          console.error(`[Alembic] Migration failed (code ${code}): ${errMsg}`);
          reject(new Error(`数据库迁移失败 (code ${code}): ${errMsg}`));
        }
      });

      proc.on('error', (err) => {
        console.error('[Alembic] Process error:', err);
        reject(new Error(`数据库迁移进程错误: ${err.message}`));
      });
    });
  }

  async createDatabase(): Promise<void> {
    const safePgDir = this.getSafePath(this.config.pgDir);
    const psql = path.join(safePgDir, 'bin', 'psql.exe');
    if (!fs.existsSync(psql)) {
      throw new Error(`PostgreSQL psql not found: ${psql}`);
    }

    const pgPort = String(this.config.pgPort);

    const execSql = (sql: string): Promise<void> => {
      return new Promise<void>((resolve, reject) => {
        const proc = this.spawnHidden(psql, ['-U', 'postgres', '-h', '127.0.0.1', '-p', pgPort, '-c', sql], {
          stdio: 'pipe',
          env: { ...process.env, PATH: `${safePgDir}\\bin;${process.env.PATH}` },
        });

        let stderr = '';
        proc.stderr?.on('data', (d: Buffer) => { stderr += d.toString(); });

        proc.on('close', (code) => {
          if (code === 0) {
            resolve();
          } else {
            console.warn(`[PostgreSQL] SQL failed (code ${code}): ${sql.trim()} — ${stderr.trim()}`);
            reject(new Error(`SQL执行失败: ${stderr.trim()}`));
          }
        });

        proc.on('error', (err) => {
          reject(new Error(`psql进程错误: ${err.message}`));
        });
      });
    };

    await execSql(`CREATE USER loan_radar WITH PASSWORD 'loan_radar_password' SUPERUSER;`).catch((err) => {
      if (!err.message.includes('already exists')) {
        console.warn('[PostgreSQL] CREATE USER warning:', err.message);
      }
    });
    await execSql(`CREATE DATABASE loan_radar OWNER loan_radar;`).catch((err) => {
      if (!err.message.includes('already exists')) {
        console.warn('[PostgreSQL] CREATE DATABASE warning:', err.message);
      }
    });
    await execSql(`GRANT ALL PRIVILEGES ON DATABASE loan_radar TO loan_radar;`).catch((err) => {
      console.warn('[PostgreSQL] GRANT warning:', err.message);
    });
  }

  async startPostgreSQL(): Promise<void> {
    const safePgDir = this.getSafePath(this.config.pgDir);
    const safePgData = this.getSafePath(this.config.pgData);

    if (!fs.existsSync(path.join(this.config.pgData, 'PG_VERSION'))) {
      throw new Error(`PostgreSQL data directory is not initialized: ${this.config.pgData}`);
    }
    this.configurePostgreSQLDataDir(this.config.pgData);

    const logDir = this.getLogDir();
    const logFile = path.join(logDir, 'pg.log');

    const pgIsReady = path.join(safePgDir, 'bin', 'pg_isready.exe');
    const pgPort = String(this.config.pgPort);

    const checkReady = (): Promise<boolean> => {
      return new Promise((resolve) => {
        if (!fs.existsSync(pgIsReady)) {
          resolve(false);
          return;
        }
        const proc = this.spawnHidden(pgIsReady, ['-h', '127.0.0.1', '-p', pgPort], {
          stdio: 'ignore',
          env: { ...process.env, PATH: `${safePgDir}\\bin;${process.env.PATH}` },
        });
        proc.on('close', (code) => resolve(code === 0));
        proc.on('error', () => resolve(false));
      });
    };

    const alreadyRunning = await checkReady();
    if (alreadyRunning) {
      console.log('[PostgreSQL] Server is already running on port', pgPort);
      return;
    }

    const pgCtl = path.join(safePgDir, 'bin', 'pg_ctl.exe');
    if (!fs.existsSync(pgCtl)) {
      throw new Error(`PostgreSQL pg_ctl.exe not found: ${pgCtl}`);
    }

    return new Promise<void>((resolve, reject) => {
      const proc = this.spawnHidden(pgCtl, [
        '-D', safePgData,
        '-l', logFile,
        'start',
      ], {
        stdio: 'pipe',
        env: { ...process.env, PATH: `${safePgDir}\\bin;${process.env.PATH}`, PGDATA: safePgData },
      });

      let stderr = '';
      proc.stderr?.on('data', (d: Buffer) => { stderr += d.toString(); });

      proc.on('close', (code) => {
        if (code !== 0 && !stderr.includes('server started') && !stderr.includes('already running')) {
          console.warn(`[PostgreSQL] pg_ctl start returned code ${code}: ${stderr}`);
        }
      });

      proc.on('error', (err) => {
        console.error('[PostgreSQL] pg_ctl error:', err);
      });

      let attempts = 0;
      const maxAttempts = 30;
      const check = () => {
        checkReady().then((ready) => {
          if (ready) {
            console.log('[PostgreSQL] Server is ready');
            resolve();
          } else if (attempts >= maxAttempts) {
            console.error('[PostgreSQL] Server failed to become ready after 15s');
            reject(new Error(`PostgreSQL 启动超时，请检查日志: ${logFile}`));
          } else {
            attempts++;
            setTimeout(check, 500);
          }
        });
      };
      check();
    });
  }

  async startBackend(): Promise<void> {
    const pythonw = this.getPythonwPath();
    const env = this.getEnv();

    const logDir = this.getLogDir();
    const logFile = path.join(logDir, 'backend.log');
    const logFd = fs.openSync(logFile, 'a');

    const proc = this.spawnHidden(pythonw, this.getPythonModuleArgs('uvicorn', [
      'app.main:app',
      '--host', '127.0.0.1',
      '--port', String(this.config.port),
    ]), {
      cwd: this.config.backendDir,
      env,
      stdio: ['ignore', logFd, logFd],
    });
    fs.closeSync(logFd);

    this.processes.set('backend', proc);

    proc.on('error', (err) => {
      console.error('[Backend] Process error:', err);
    });

    proc.on('close', (code) => {
      console.log(`[Backend] Process exited with code ${code}`);
      this.processes.delete('backend');
    });
  }

  async startMediaCrawler(): Promise<void> {
    const pythonw = this.getPythonwPath();
    const env = this.getEnv();

    const mainFile = path.join(this.config.mediacrawlerDir, 'api', 'main.py');
    if (!fs.existsSync(mainFile)) {
      return;
    }

    const logDir = this.getLogDir();
    const logFile = path.join(logDir, 'mediacrawler.log');
    const logFd = fs.openSync(logFile, 'a');

    const proc = this.spawnHidden(pythonw, this.getPythonModuleArgs('uvicorn', [
      'api.main:app',
      '--host', '127.0.0.1',
      '--port', '8080',
    ]), {
      cwd: this.config.mediacrawlerDir,
      env,
      stdio: ['ignore', logFd, logFd],
    });
    fs.closeSync(logFd);

    this.processes.set('mediacrawler', proc);

    proc.on('error', (err) => {
      console.error('[MediaCrawler] Process error:', err);
    });

    proc.on('close', (code) => {
      console.log(`[MediaCrawler] Process exited with code ${code}`);
      this.processes.delete('mediacrawler');
    });
  }

  async stopAll(): Promise<void> {
    const forceKill = (pid: number | undefined) => {
      if (pid) {
        try {
          this.spawnHidden('taskkill', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore' });
        } catch {}
      }
    };

    const backendProc = this.processes.get('backend');
    const mcProc = this.processes.get('mediacrawler');

    if (backendProc) {
      forceKill(backendProc.pid);
      this.processes.delete('backend');
    }
    if (mcProc) {
      forceKill(mcProc.pid);
      this.processes.delete('mediacrawler');
    }

    const safePgDir = this.getSafePath(this.config.pgDir);
    const safePgData = this.getSafePath(this.config.pgData);
    const pgCtl = path.join(safePgDir, 'bin', 'pg_ctl.exe');
    if (fs.existsSync(pgCtl)) {
      this.spawnHidden(pgCtl, [
        '-D', safePgData,
        '-m', 'immediate',
        'stop',
      ], {
        stdio: 'ignore',
        env: { ...process.env, PATH: `${safePgDir}\\bin;${process.env.PATH}`, PGDATA: safePgData },
      });
    }
  }
}
