import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import {readFile, writeFile} from 'node:fs/promises';
import path from 'path';
import {defineConfig, type Plugin} from 'vite';

const injectServiceWorkerPrecache = (): Plugin => {
  let outputDirectory: string | undefined;
  return {
    name: 'maizecare-service-worker-precache',
    configResolved(config) {
      if (config.command === 'build') outputDirectory = path.resolve(config.root, config.build.outDir);
    },
    async closeBundle() {
      if (!outputDirectory) return;

      const manifestPath = path.join(outputDirectory, '.vite', 'manifest.json');
      const manifest = JSON.parse(await readFile(manifestPath, 'utf8')) as Record<string, {
        src?: string;
        file?: string;
        css?: string[];
        imports?: string[];
        dynamicImports?: string[];
        isEntry?: boolean;
      }>;
      const findManifestKey = (source: string): string | undefined =>
        Object.keys(manifest).find((key) => key === source || manifest[key].src === source);
      const entryKey = findManifestKey('src/main.tsx') ??
        findManifestKey('index.html') ??
        Object.keys(manifest).find((key) => manifest[key].isEntry);
      if (!entryKey) throw new Error('Vite manifest is missing the frontend entry point.');

      const criticalAssets = new Set<string>();
      const visited = new Set<string>();
      const visit = (key: string, includeDynamicImports: boolean): void => {
        const visitKey = `${key}:${includeDynamicImports}`;
        if (visited.has(visitKey)) return;
        visited.add(visitKey);
        const asset = manifest[key];
        if (!asset) throw new Error(`Vite manifest is missing an imported asset: ${key}`);
        if (asset.file) criticalAssets.add(asset.file);
        asset.css?.forEach((fileName) => criticalAssets.add(fileName));
        asset.imports?.forEach((dependency) => visit(dependency, includeDynamicImports));
        if (includeDynamicImports && key !== entryKey) {
          asset.dynamicImports?.forEach((dependency) => visit(dependency, true));
        }
      };

      visit(entryKey, false);
      for (const offlineRoute of [
        'src/pages/FarmerDashboardPage.tsx',
        'src/pages/DiagnosisPage.tsx',
        'src/pages/DiagnosisResultPage.tsx',
      ]) {
        const key = findManifestKey(offlineRoute);
        if (!key) throw new Error(`Vite manifest is missing the offline route: ${offlineRoute}`);
        visit(key, true);
      }

      const workerPath = path.join(outputDirectory, 'service-worker.js');
      const source = await readFile(workerPath, 'utf8');
      await writeFile(workerPath, source.replace(
        "'__MAIZECARE_CRITICAL_ASSETS__'",
        JSON.stringify([...criticalAssets]),
      ));
      },
    };
};

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss(), injectServiceWorkerPrecache()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
    build: {
      manifest: true,
    },
  };
});
