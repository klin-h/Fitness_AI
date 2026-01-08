# MediaPipe 网络连接超时问题解决方案

## 问题描述

MediaPipe 资源从 CDN 加载时出现 `ERR_CONNECTION_TIMED_OUT` 错误，导致姿态检测功能无法使用。

## 原因分析

1. **网络连接问题**：无法访问 `cdn.jsdelivr.net`
2. **CDN 服务不稳定**：某些地区访问 jsdelivr CDN 可能较慢或不稳定
3. **防火墙/代理限制**：公司或学校网络可能阻止了 CDN 访问

## 解决方案

### 方案1：使用备用 CDN（已实施）

已修改代码使用 `unpkg.com` CDN，通常比 `jsdelivr.net` 更稳定：

```typescript
locateFile: (file) => {
  return `https://unpkg.com/@mediapipe/pose@0.5.1675469404/${file}`;
}
```

### 方案2：使用本地文件（推荐用于生产环境）

1. **复制 MediaPipe 文件到 public 目录**：
   ```bash
   # 在项目根目录执行
   mkdir -p frontend/public/mediapipe
   cp -r frontend/node_modules/@mediapipe/pose/* frontend/public/mediapipe/
   ```

2. **修改 locateFile**：
   ```typescript
   locateFile: (file) => {
     return `/mediapipe/${file}`;
   }
   ```

### 方案3：配置代理（开发环境）

如果使用代理，可以在 `package.json` 中配置：

```json
{
  "proxy": "http://your-proxy-server:port"
}
```

或在启动时设置环境变量：

```bash
# Windows PowerShell
$env:HTTP_PROXY="http://proxy:port"
$env:HTTPS_PROXY="http://proxy:port"
npm start

# Mac/Linux
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
npm start
```

### 方案4：使用离线模式

1. **下载 MediaPipe 文件**：
   - 访问：https://unpkg.com/@mediapipe/pose@0.5.1675469404/
   - 下载以下文件：
     - `pose_web.binarypb`
     - `pose_solution_simd_wasm_bin.js`
     - `pose_solution_simd_wasm_bin.wasm`
     - `pose_solution_packed_assets_loader.js`

2. **放置到 public 目录**：
   ```
   frontend/public/mediapipe/
   ├── pose_web.binarypb
   ├── pose_solution_simd_wasm_bin.js
   ├── pose_solution_simd_wasm_bin.wasm
   └── pose_solution_packed_assets_loader.js
   ```

3. **修改代码**：
   ```typescript
   locateFile: (file) => {
     return `/mediapipe/${file}`;
   }
   ```

## 当前实施

已修改 `frontend/src/hooks/usePoseDetection.ts`，使用 `unpkg.com` CDN 作为主要源。

## 验证修复

1. **清除浏览器缓存**：
   - Chrome: `Ctrl+Shift+Delete` → 清除缓存
   - Firefox: `Ctrl+Shift+Delete` → 清除缓存

2. **刷新页面**：
   - 硬刷新：`Ctrl+F5` 或 `Ctrl+Shift+R`

3. **检查控制台**：
   - 应该不再看到 `ERR_CONNECTION_TIMED_OUT` 错误
   - MediaPipe 资源应该从 `unpkg.com` 加载

4. **测试功能**：
   - 点击"开始检测"
   - 应该能看到骨骼点显示

## 如果问题仍然存在

### 检查网络连接

```bash
# 测试 unpkg.com 连接
ping unpkg.com

# 测试 jsdelivr.net 连接
ping cdn.jsdelivr.net
```

### 使用浏览器开发者工具

1. 打开浏览器开发者工具（F12）
2. 切换到 Network（网络）标签
3. 刷新页面
4. 查看哪些资源加载失败
5. 尝试手动访问失败的 URL

### 临时解决方案

如果所有 CDN 都无法访问，可以：

1. **使用手机热点**：切换到移动网络
2. **使用 VPN**：连接到其他地区的服务器
3. **使用本地文件**：按照方案2或方案4实施

## 生产环境建议

对于生产环境，强烈建议：

1. **将 MediaPipe 文件打包到构建输出**：
   ```bash
   # 在构建脚本中添加
   cp -r node_modules/@mediapipe/pose/* public/mediapipe/
   ```

2. **使用本地路径**：
   ```typescript
   locateFile: (file) => {
     // 生产环境使用本地文件
     if (process.env.NODE_ENV === 'production') {
       return `/mediapipe/${file}`;
     }
     // 开发环境使用 CDN
     return `https://unpkg.com/@mediapipe/pose@0.5.1675469404/${file}`;
   }
   ```

3. **配置 CDN 回退**：
   ```typescript
   locateFile: async (file) => {
     const localPath = `/mediapipe/${file}`;
     try {
       // 尝试加载本地文件
       await fetch(localPath, { method: 'HEAD' });
       return localPath;
     } catch {
       // 回退到 CDN
       return `https://unpkg.com/@mediapipe/pose@0.5.1675469404/${file}`;
     }
   }
   ```

