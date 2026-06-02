const assert = require("assert");

const {
  DEFAULT_POSTGRES_PORT,
  buildDatabaseUrl,
  getEmbeddedPlaywrightNodeDir,
  prependPathEntries,
  buildPythonImportPath,
} = require("../dist/desktop-config");

assert.strictEqual(
  DEFAULT_POSTGRES_PORT,
  55432,
  "Packaged desktop builds should avoid the public PostgreSQL 5432 port",
);

assert.strictEqual(
  buildDatabaseUrl(55432),
  "postgresql+psycopg2://loan_radar:loan_radar_password@127.0.0.1:55432/loan_radar",
);

assert.strictEqual(
  buildPythonImportPath(["C:\\app\\backend", "C:\\app", "C:\\app\\backend"]),
  ["C:\\app\\backend", "C:\\app"].join(require("path").delimiter),
  "Python bootstrap path should preserve order and remove duplicates",
);

assert.strictEqual(
  getEmbeddedPlaywrightNodeDir("C:\\app\\tools\\python"),
  require("path").join("C:\\app\\tools\\python", "Lib", "site-packages", "playwright", "driver"),
);

assert.strictEqual(
  prependPathEntries(
    ["C:\\Windows\\System32", "C:\\app\\tools\\python"].join(require("path").delimiter),
    ["C:\\app\\tools\\python", "C:\\app\\tools\\python\\Scripts"],
  ),
  ["C:\\app\\tools\\python", "C:\\app\\tools\\python\\Scripts", "C:\\Windows\\System32"].join(require("path").delimiter),
  "Process PATH should prepend tool dirs and remove duplicate entries",
);

console.log("desktop-config tests passed");
