import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: './',
  // 数据集就在仓库根目录的 data/，构建时原样拷进 dist 根，仓库里只有这一份
  publicDir: 'data',
  build: { outDir: 'dist', assetsDir: 'assets', emptyOutDir: true }
})
