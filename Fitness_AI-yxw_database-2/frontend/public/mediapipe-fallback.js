/**
 * MediaPipe 资源加载备用方案
 * 如果 CDN 加载失败，尝试使用本地文件或备用 CDN
 */

// 检测 MediaPipe 资源是否加载成功
window.mediapipeLoadCheck = {
  failed: [],
  retries: 0,
  maxRetries: 3
};

// 监听资源加载失败
window.addEventListener('error', (event) => {
  if (event.target && event.target.src) {
    const src = event.target.src;
    if (src.includes('@mediapipe') || src.includes('mediapipe')) {
      console.warn('MediaPipe 资源加载失败:', src);
      window.mediapipeLoadCheck.failed.push(src);
    }
  }
}, true);

// 提供备用加载函数
window.loadMediaPipeResource = async (file, basePath = '/node_modules/@mediapipe/pose/') => {
  const mirrors = [
    basePath + file, // 本地路径
    `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
    `https://unpkg.com/@mediapipe/pose/${file}`,
    `https://cdn.skypack.dev/@mediapipe/pose/${file}`
  ];
  
  for (const url of mirrors) {
    try {
      const response = await fetch(url, { method: 'HEAD' });
      if (response.ok) {
        console.log(`✅ MediaPipe 资源加载成功: ${url}`);
        return url;
      }
    } catch (error) {
      console.warn(`❌ MediaPipe 资源加载失败: ${url}`, error);
      continue;
    }
  }
  
  throw new Error(`所有 MediaPipe 资源镜像都加载失败: ${file}`);
};

