import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, "data");
const ML_DATA_DIR = path.join(__dirname, "..", "simulation", "ml_artifacts");
const ML_MODEL_DIR = path.join(__dirname, "..", "simulation", "ml");

function serveGeneratedData(prefix: string, rootDir: string): Plugin {
  return {
    name: `serve-generated-data-${prefix.replace(/\W+/g, "")}`,
    configureServer(server) {
      server.middlewares.use(prefix, (req, res) => {
        const url = ((req.url as string | undefined) ?? "").split("?")[0];
        const filePath = path.join(rootDir, url);
        const relativePath = path.relative(rootDir, filePath);
        if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
          res.statusCode = 403;
          res.end("forbidden");
          return;
        }
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
          const ext = path.extname(filePath);
          res.setHeader(
            "Content-Type",
            ext === ".json" ? "application/json" : "text/csv",
          );
          fs.createReadStream(filePath).pipe(res);
        } else {
          res.statusCode = 404;
          res.end("not found");
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    serveGeneratedData("/data", DATA_DIR),
    serveGeneratedData("/ml-data", ML_DATA_DIR),
    serveGeneratedData("/ml-model", ML_MODEL_DIR),
  ],
  server: {
    port: 5173,
    host: true,
  },
});
