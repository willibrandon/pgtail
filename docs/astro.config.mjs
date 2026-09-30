// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
  site: 'https://pgtail.dev',
  vite: {
    build: {
      rolldownOptions: {
        // Astro starts each MDX page's asset module with a "use astro:head-inject" directive that nothing reads any
        // more, and rolldown warns that bundling may not keep it. Only that warning is dropped; remove this once Astro
        // ships https://github.com/withastro/astro/pull/18088.
        onLog(level, log, handler) {
          if (log.code === 'MODULE_LEVEL_DIRECTIVE' && log.message.includes('"use astro:head-inject"')) {
            return;
          }

          handler(level, log);
        },
      },
    },
  },
  integrations: [
    starlight({
      title: 'pgtail',
      description: 'Interactive PostgreSQL log tailer with auto-detection and color output.',
      logo: { light: './src/assets/logo-light.svg', dark: './src/assets/logo-dark.svg', alt: 'pgtail' },
      favicon: '/favicon.png',
      social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/willibrandon/pgtail' }],
      customCss: ['./src/styles/custom.css'],
      // src/pages/404.astro is the not found page.
      disable404Route: true,
      sidebar: [
        {
          label: 'Getting started',
          items: [
            { label: 'Installation', slug: 'getting-started/installation' },
            { label: 'Quick start', slug: 'getting-started/quickstart' },
          ],
        },
        {
          label: 'Guide',
          items: [
            { label: 'Tail mode', slug: 'guide/tail-mode' },
            { label: 'Log formats', slug: 'guide/log-formats' },
            { label: 'Filtering', slug: 'guide/filtering' },
            { label: 'Time filters', slug: 'guide/time-filters' },
            { label: 'Slow queries', slug: 'guide/slow-queries' },
            { label: 'Highlighting', slug: 'guide/highlighting' },
            { label: 'Notifications', slug: 'guide/notifications' },
            { label: 'Themes', slug: 'guide/themes' },
            { label: 'Export and pipe', slug: 'guide/export' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'Configuration', slug: 'configuration' },
            { label: 'Command line', slug: 'cli-reference' },
          ],
        },
      ],
    }),
  ],
});
