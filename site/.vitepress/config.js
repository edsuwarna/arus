import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Arus',
  description: 'Lightweight, self-hosted CDC & ETL platform — data flows without the cluster.',
  lang: 'en-US',
  ignoreDeadLinks: true,

  themeConfig: {
    logo: { src: '/arus-icon.svg', width: 28, height: 28 },

    nav: [
      { text: 'Docs', link: '/guide/' },
      { text: 'Architecture', link: '/guide/architecture' },
      { text: 'API', link: '/reference/api' },
      { text: 'GitHub', link: 'https://github.com/edsuwarna/arus' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Overview', link: '/guide/' },
            { text: 'Quickstart', link: '/guide/quickstart' },
          ],
        },
        {
          text: 'Architecture',
          items: [
            { text: 'System Design', link: '/guide/architecture' },
          ],
        },
        {
          text: 'Guides',
          items: [
            { text: 'Connectors', link: '/guide/connectors' },
            { text: 'Pipelines', link: '/guide/pipelines' },
            { text: 'Console', link: '/guide/console' },
            { text: 'Deployment', link: '/guide/deployment' },
            { text: 'Development', link: '/guide/development' },
          ],
        },
      ],
      '/reference/': [
        {
          text: 'Reference',
          items: [
            { text: 'API Reference', link: '/reference/api' },
            { text: 'Configuration', link: '/reference/configuration' },
            { text: 'Data Model', link: '/reference/datamodel' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/edsuwarna/arus' },
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024-2026 Endang Suwarna',
    },

    search: {
      provider: 'local',
    },
  },

  // Override VitePress dark theme colors to match Arus branding
  appearance: 'dark',
})
