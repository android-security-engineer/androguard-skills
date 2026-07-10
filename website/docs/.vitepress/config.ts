import { defineConfig } from 'vitepress'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// 命令清单数据源 —— 由 scripts/introspect_commands.py 从 click 命令树内省生成
// 用 process.cwd() 定位（vitepress build 在 website/ 目录执行）
const commandsData = JSON.parse(
  readFileSync(resolve(process.cwd(), 'scripts/commands.json'), 'utf-8'),
)

// 仓库信息 —— 用于 GitHub Pages 部署的 base 路径与编辑链接
// 本仓库：https://github.com/android-security-engineer/androguard-skills
// 部署到 https://android-security-engineer.github.io/androguard-skills/
// CI（deploy_docs.yml）会根据 GITHUB_REPOSITORY 再次覆盖此 base 值（自适应仓库名）；
// 这里默认值固化为本仓库 repo 名，保证本地预览与 CI 一致，即使 sed 失败也不致路径错乱。
const repo = 'android-security-engineer/androguard-skills'
const repoUrl = `https://github.com/${repo}`
const pagesUrl = `https://android-security-engineer.github.io/androguard-skills/`
const base = `/androguard-skills/`

// 各命令组的中文标题
const GROUP_TITLES: Record<string, string> = {
  daemon: 'daemon · 进程管理',
  apk: 'apk · APK 信息',
  dex: 'dex · DEX 信息',
  analysis: 'analysis · 静态分析',
  decompile: 'decompile · 反编译',
  pentest: 'pentest · 动态分析',
  resources: 'resources · 资源解析',
  visualize: 'visualize · 可视化',
  util: 'util · 工具',
  session: 'session · 会话',
}

// 生成某个命令组的侧边栏条目（组概览 + 每个命令）
function groupSidebar(group: string) {
  const cmds = (commandsData as any)[group]?.commands ?? []
  return {
    text: `${GROUP_TITLES[group]}（${cmds.length}）`,
    collapsed: true,
    items: [
      { text: '组概览', link: `/commands/${group}/` },
      ...cmds.map((c: any) => ({ text: c.name, link: `/commands/${group}/${c.name}` })),
    ],
  }
}

export default defineConfig({
  lang: 'zh-CN',
  title: 'Androguard Skills',
  description: 'Android 逆向工程能力的 JSON CLI —— 219 个命令、daemon 模式、一键安全审计',
  base,
  // GitHub Pages 部署：srcRoot=docs（由命令行 vitepress build docs 指定），
  // outDir 相对 srcRoot，产物在 website/docs/.vitepress/dist
  outDir: '.vitepress/dist',
  cleanDist: true,
  lastUpdated: true,

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: `${base}android-icon.svg` }],
    ['meta', { name: 'theme-color', content: '#3DDC84' }],
  ],

  markdown: {
    lineNumbers: false,
    // 支持常规代码高亮；额外语言见下
    languages: ['bash', 'python', 'json', 'yaml', 'toml', 'markdown'],
  },

  themeConfig: {
    // 站点 logo（导航栏左侧）
    logo: '/android-icon.svg',

    siteTitle: 'Androguard Skills',

    // 导航栏
    nav: [
      { text: '指南', link: '/guide/introduction', activeMatch: '/guide/' },
      { text: '命令参考', link: '/commands/', activeMatch: '/commands/' },
      { text: '代码模块', link: '/modules/', activeMatch: '/modules/' },
      { text: '安全审计', link: '/audit/overview', activeMatch: '/audit/' },
      { text: 'GitHub', link: repoUrl },
    ],

    // 搜索
    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索文档', buttonAriaLabel: '搜索文档', buttonWidth: 40 },
          modal: {
            noResultsText: '无法找到相关结果',
            resetButtonTitle: '清除查询条件',
            footer: { selectText: '选择', navigateText: '切换', closeText: '关闭' },
          },
        },
      },
    },

    // 侧边栏：按顶层目录分别配置
    sidebar: {
      '/guide/': [
        {
          text: '开始',
          collapsed: false,
          items: [
            { text: '项目简介', link: '/guide/introduction' },
            { text: '它能解决什么问题', link: '/guide/what-it-solves' },
            { text: '安装', link: '/guide/installation' },
            { text: '快速开始', link: '/guide/quick-start' },
            { text: '架构总览', link: '/guide/architecture' },
          ],
        },
        {
          text: '运行模式',
          collapsed: false,
          items: [
            { text: '单次执行模式', link: '/guide/standalone-mode' },
            { text: 'Daemon 模式', link: '/guide/daemon-mode' },
            { text: '内存管理（长跑）', link: '/guide/memory-management' },
            { text: 'JSON-RPC 协议', link: '/guide/jsonrpc-protocol' },
          ],
        },
        {
          text: '数据与输出',
          collapsed: false,
          items: [
            { text: '输出格式规范', link: '/guide/output-format' },
            { text: '类名与描述符', link: '/guide/class-descriptors' },
            { text: '资源 ID 体系', link: '/guide/resource-ids' },
          ],
        },
        {
          text: '进阶',
          collapsed: false,
          items: [
            { text: 'Python API', link: '/guide/python-api' },
            { text: '常见工作流', link: '/guide/workflows' },
            { text: 'FAQ', link: '/guide/faq' },
          ],
        },
      ],

      '/commands/': [
        {
          text: '命令总览',
          items: [{ text: '219 个命令索引', link: '/commands/' }],
        },
        // 顶层命令
        {
          text: '顶层命令',
          collapsed: false,
          items: [
            { text: 'load', link: '/commands/load' },
            { text: 'load-dex', link: '/commands/load-dex' },
            { text: 'unload', link: '/commands/unload' },
          ],
        },
        // 各组：动态从 commands.json 生成（组概览 + 每命令一条）
        groupSidebar('daemon'),
        groupSidebar('apk'),
        groupSidebar('dex'),
        groupSidebar('analysis'),
        groupSidebar('decompile'),
        groupSidebar('pentest'),
        groupSidebar('resources'),
        groupSidebar('visualize'),
        groupSidebar('util'),
        groupSidebar('session'),
      ],

      '/modules/': [
        { text: '模块地图', items: [{ text: '代码模块总览', link: '/modules/' }] },
        { text: 'main.py · CLI 入口', items: [{ text: 'main 模块', link: '/modules/main' }] },
        { text: '业务模块', collapsed: false, items: [
          { text: 'apk_skills', link: '/modules/apk-skills' },
          { text: 'dex_skills', link: '/modules/dex-skills' },
          { text: 'analysis_skills', link: '/modules/analysis-skills' },
          { text: 'decompiler_skills', link: '/modules/decompiler-skills' },
          { text: 'resource_skills', link: '/modules/resource-skills' },
          { text: 'session_skills', link: '/modules/session-skills' },
          { text: 'util_skills', link: '/modules/util-skills' },
          { text: 'visualize_skills', link: '/modules/visualize-skills' },
          { text: 'pentest_skills', link: '/modules/pentest-skills' },
        ]},
        { text: '基础设施', collapsed: false, items: [
          { text: 'daemon', link: '/modules/daemon' },
        ]},
      ],

      '/audit/': [
        { text: '安全审计套件', items: [
          { text: '审计总览', link: '/audit/overview' },
          { text: '一键安全报告', link: '/audit/security-report' },
          { text: '攻击面分析', link: '/audit/attack-surface' },
          { text: 'OWASP 映射', link: '/audit/owasp-mapping' },
          { text: '污点路径', link: '/audit/taint-path' },
          { text: '反分析与加固', link: '/audit/anti-analysis' },
        ]},
      ],
    },

    // 社交链接（导航栏右侧图标）
    socialLinks: [
      { icon: 'github', link: repoUrl },
    ],

    // 页脚
    footer: {
      message: '基于 Apache-2.0 协议发布 · 文档站部署于 GitHub Pages',
      copyright: 'Copyright © 2024 Androguard Skills',
    },

    // 文档修订时间
    lastUpdated: {
      text: '最后更新',
    },

    // 文档页内大纲
    outline: {
      level: [2, 3],
      label: '本页内容',
    },

    // 上一页/下一页
    docFooter: {
      prev: '上一页',
      next: '下一页',
    },

    // 404 页
    notFound: {
      title: '页面不存在',
      quote: '找不到这个命令或文档，但它一定存在于 219 个命令中的某个角落。',
      linkLabel: '回到首页',
    },

    // 编辑此页链接
    editLink: {
      pattern: `${repoUrl}/edit/master/website/docs/:path`,
      text: '在 GitHub 上编辑此页',
    },
  },
})
