import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import {readdir, readFile, writeFile} from 'node:fs/promises';
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

      const outputDir = outputDirectory;
    const files: string[] = [];
    const walk = async (directory: string): Promise<void> => {
      for (const entry of await readdir(directory, {withFileTypes: true})) {
        const absolutePath = path.join(directory, entry.name);
        if (entry.isDirectory()) await walk(absolutePath);
        else files.push(path.relative(outputDir, absolutePath).split(path.sep).join('/'));
      }
    };
    await walk(outputDir);

    const criticalAssets = files.filter((fileName) =>
      fileName !== 'service-worker.js' && /\.(?:m?js|css)$/i.test(fileName)
    );
    const optionalAssets = files.filter((fileName) =>
      /\.(?:avif|gif|jpe?g|png|svg|webp|woff2?)$/i.test(fileName)
    );
    const workerPath = path.join(outputDir, 'service-worker.js');
    const source = await readFile(workerPath, 'utf8');
      await writeFile(workerPath, source
        .replace("'__MAIZECARE_CRITICAL_ASSETS__'", JSON.stringify(criticalAssets))
        .replace("'__MAIZECARE_OPTIONAL_ASSETS__'", JSON.stringify(optionalAssets)));
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
  };
});
