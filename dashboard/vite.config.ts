import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, "data");

// Serve the existing `dashboard/data/` folder (populated by the simulator's
// data pipeline) as static files under `/data/*`. This keeps the generated
// CSVs out of `public/` while still letting the browser fetch them.
function dataMiddleware(): Plugin {
  return {
    name: "serve-data",
    configureServer(server) {
      server.middlewares.use("/data", (req, res, next) => {
        const url = ((req.url as string | undefined) ?? "").split("?")[0];
        const filePath = path.join(DATA_DIR, url);
        if (!filePath.startsWith(DATA_DIR)) {
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
          next();
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), dataMiddleware()],
  server: {
    port: 5173,
    host: true,
  },
});
