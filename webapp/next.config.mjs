import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  outputFileTracingIncludes: {
    "/api/v1/**": [
      path.join(__dirname, "python", "**", "*.py"),
      path.join(__dirname, "..", "sdk", "python", "src", "migrator_gen", "**", "*.py"),
      path.join(__dirname, "..", "migration-packs", "*.json"),
    ],
  },
  experimental: {
    serverComponentsExternalPackages: ["pyodide"],
  },
};

export default nextConfig;
