// MOSE Tauri Bridge：让 web/editor.js 不改一行就能在 Tauri 里跑。
//
// 三件事：
// 1. Monkey-patch fetch：mose:// URL → Tauri invoke
// 2. 拦截"打开工程"按钮 + "最近工程"切换：用 Tauri 拿真实路径，模拟 file input
// 3. 拦截 reload + 自动加载关联媒体
//
// 通过 Rust include_str! 嵌入到 index.html 的 </body> 前（editor.js 之后执行）。
(function () {
  'use strict';

  var invoke =
    (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) ||
    null;

  if (!invoke) {
    console.error('[MOSE] window.__TAURI__.core.invoke 不可用，IPC 无法工作');
    return;
  }

  // === 工具函数 ===

  function okResponse(data) {
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  function errResponse(message) {
    return new Response(
      JSON.stringify({ ok: false, error: String(message) }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }

  // 把工程数据注入 editor.js（模拟 file input change）+ 启用保存 + 自动加载媒体
  function loadProjectData(result) {
    if (!result || !result.ok) {
      if (result && result.error) {
        alert(result.error);
      }
      return;
    }

    var fileInput = document.getElementById('open-project-file');
    if (!fileInput) return;

    var jsonContent = JSON.stringify(result.data);
    var file = new File([jsonContent], result.filename || 'untitled.mosp', {
      type: 'application/json',
    });
    var dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    fileInput.dispatchEvent(new Event('change', { bubbles: true }));

    // 启用"保存工程"按钮 + 实时更新最近工程列表
    if (typeof SERVER_CONFIG !== 'undefined') {
      SERVER_CONFIG.canSave = true;
      // 把刚打开的工程加到最近列表头部（去重）
      if (!Array.isArray(SERVER_CONFIG.recentProjects)) SERVER_CONFIG.recentProjects = [];
      SERVER_CONFIG.recentProjects = SERVER_CONFIG.recentProjects.filter(function (p) {
        return p.path !== result.path;
      });
      SERVER_CONFIG.recentProjects.unshift({
        path: result.path, name: result.filename, exists: true,
      });
    }
    var saveDropdown = document.getElementById('save-project-dropdown');
    if (saveDropdown) saveDropdown.hidden = false;
    var saveBtn = document.getElementById('save-project');
    if (saveBtn) saveBtn.disabled = false;

    // 重新渲染最近工程下拉列表（让新打开的工程立刻可见）
    if (typeof configureRecentProjects === 'function') {
      configureRecentProjects();
    }

    // 自动加载关联媒体（如果有 media 路径）
    if (result.data && result.data.media) {
      autoLoadMedia(result.data.media);
    }
  }

  // 自动加载媒体：关闭 editor.js 弹出的"选择媒体" modal，然后设置 player.src
  async function autoLoadMedia(mediaPath) {
    if (!mediaPath) return;
    try {
      var result = await invoke('resolve_media', { path: mediaPath });
      if (!result || !result.ok) {
        console.warn('[MOSE] 媒体加载失败:', result ? result.error : 'unknown');
        return;
      }

      // 等 editor.js 弹出"选择关联媒体" modal 后自动关闭它
      setTimeout(function () {
        var laterBtn = document.getElementById('project-media-later');
        if (laterBtn) laterBtn.click();

        // 设置 player 媒体源
        var player = document.getElementById('player');
        if (player) {
          var source = player.querySelector('source');
          if (source) source.src = result.url;
          else player.src = result.url;
          player.load();
        }

        // 更新标题里的媒体名
        var mediaNameEl = document.getElementById('media-name');
        if (mediaNameEl) {
          mediaNameEl.textContent = result.name;
          mediaNameEl.classList.remove('empty');
          mediaNameEl.title = '点击复制媒体名：' + result.name;
        }

        console.log('[MOSE] 媒体已自动加载:', result.name);
      }, 300);
    } catch (e) {
      console.warn('[MOSE] 媒体加载异常:', e);
    }
  }

  // === 1. Monkey-patch fetch ===

  var originalFetch = window.fetch;

  window.fetch = async function (url, options) {
    options = options || {};
    var urlStr = String(url);
    var body = {};
    try {
      body = JSON.parse(options.body || '{}');
    } catch (e) {}

    try {
      if (urlStr.indexOf('mose://save-project') !== -1) {
        return okResponse(await invoke('save_project', body));
      }
      if (urlStr.indexOf('mose://recent-projects') !== -1) {
        // "最近工程"切换：不只是记录路径，还要真正打开工程
        var result = await invoke('open_project_at_path', body);
        if (result && result.ok) {
          loadProjectData(result);
        }
        return okResponse(result);
      }
      if (urlStr.indexOf('mose://settings') !== -1) {
        return okResponse(await invoke('update_settings', body));
      }
    } catch (error) {
      return errResponse(error);
    }

    return originalFetch.call(this, url, options);
  };

  // === 2. 拦截 window.location.reload ===
  // Tauri 模式下 index.html 只在启动时渲染一次，reload 不会更新数据。
  // 数据已通过 loadProjectData 注入，直接忽略 reload。

  window.location.reload = function () {
    console.log('[MOSE] reload 已拦截（Tauri 模式用数据注入替代）');
  };

  // === 3. 拦截"打开工程"按钮 ===

  function setupOpenProjectInterceptor() {
    var openBtn = document.getElementById('open-project');
    if (!openBtn) {
      setTimeout(setupOpenProjectInterceptor, 50);
      return;
    }

    openBtn.addEventListener(
      'click',
      async function (e) {
        e.stopImmediatePropagation();
        try {
          var result = await invoke('open_project');
          if (!result || !result.ok || result.cancelled) return;
          loadProjectData(result);
        } catch (error) {
          console.error('[MOSE] 打开工程失败:', error);
        }
      },
      true
    );

    console.log('[MOSE] "打开工程"拦截器已就绪');
  }

  setupOpenProjectInterceptor();
  console.log('[MOSE] Tauri bridge initialized (fetch→invoke + open + media + reload)');
})();
