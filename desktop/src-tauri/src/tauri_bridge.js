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

  // 把工程数据注入 editor.js：直接调 openProjectFile（全局函数），不模拟 file input。
  // openProjectFile 处理完后（.then），启用保存 + 更新最近工程 + 自动加载媒体。
  function loadProjectData(result) {
    if (!result || !result.ok) {
      if (result && result.error) {
        alert(result.error);
      }
      return;
    }

    var jsonContent = JSON.stringify(result.data);
    var file = new File([jsonContent], result.filename || 'untitled.mosp', {
      type: 'application/json',
    });

    if (typeof openProjectFile === 'function') {
      openProjectFile(file, [], null).then(function (success) {
        if (!success) return;

        // 启用保存按钮 + 实时更新最近工程
        if (typeof SERVER_CONFIG !== 'undefined') {
          SERVER_CONFIG.canSave = true;
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

        if (typeof configureRecentProjects === 'function') {
          configureRecentProjects();
        }

        // 自动加载关联媒体
        if (result.data && result.data.media) {
          autoLoadMedia(result.data.media);
        }
      });
    } else {
      console.error('[MOSE] openProjectFile 函数不可用');
    }
  }

  // 自动加载媒体：用 invoke('resolve_media') 获取 file:// URL，直接设 player.src。
  // 直接调 openProjectFile 不经过 change handler，不会弹"选择媒体" modal。
  async function autoLoadMedia(mediaPath) {
    if (!mediaPath) return;
    try {
      var result = await invoke('resolve_media', { path: mediaPath });
      if (!result || !result.ok) {
        console.warn('[MOSE] 媒体加载失败:', result ? result.error : 'unknown');
        return;
      }

      var player = document.getElementById('player');
      if (player) {
        var source = player.querySelector('source');
        if (source) source.src = result.url;
        else player.src = result.url;
        player.load();
      }

      var mediaNameEl = document.getElementById('media-name');
      if (mediaNameEl) {
        mediaNameEl.textContent = result.name;
        mediaNameEl.classList.remove('empty');
        mediaNameEl.title = '点击复制媒体名：' + result.name;
      }

      console.log('[MOSE] 媒体已自动加载:', result.name);

      // 自动提取波形（调 ffmpeg sidecar，非致命——失败不影响编辑器使用）
      try {
        var wave = await invoke('extract_waveform', { mediaPath: mediaPath });
        if (wave && wave.data) {
          if (typeof DATA !== 'undefined') {
            DATA.waveform = wave;
          }
          if (typeof waveformEditor !== 'undefined' && waveformEditor) {
            waveformEditor.setPayload(wave);
          }
          console.log('[MOSE] 波形已生成:', wave.peak_count, 'peaks');
        }
      } catch (waveErr) {
        console.warn('[MOSE] 波形提取失败（非致命）:', waveErr);
      }
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

  // === 4. 拦截"📁 浏览…"表情包按钮 ===
  // editor.js 的 sticker-root-pick 用浏览器 showDirectoryPicker/webkitdirectory（拿不到路径，用 blob URL）。
  // Tauri 模式改为 dialog 选目录 + Rust 扫描 → file:// URL 直接加载图片。
  function setupStickerInterceptor() {
    var pickBtn = document.getElementById('sticker-root-pick');
    if (!pickBtn) {
      setTimeout(setupStickerInterceptor, 50);
      return;
    }

    pickBtn.addEventListener(
      'click',
      async function (e) {
        e.stopImmediatePropagation();

        try {
          var result = await invoke('pick_and_scan_stickers');
          if (!result || !result.ok || result.cancelled) return;

          // 更新 STICKERS 数组（file:// URL，不需要 blob URL）
          if (typeof STICKERS !== 'undefined') {
            STICKERS.forEach(function (s) {
              if (s._blobUrl) { try { URL.revokeObjectURL(s._blobUrl); } catch (e) {} }
            });
            STICKERS.length = 0;
            result.stickers.forEach(function (s) { STICKERS.push(s); });
          }

          // STICKER_ROOT 改为实际路径（editor.js stickerUrl 会拼 file:// URL）
          if (typeof STICKER_ROOT !== 'undefined') {
            STICKER_ROOT = result.root;
          }

          var input = document.getElementById('sticker-root-input');
          if (input) input.value = result.root;
          var modal = document.getElementById('sticker-root-modal');
          if (modal) modal.classList.remove('show');

          if (typeof renderAll === 'function') renderAll();
          if (typeof flashHint === 'function') {
            flashHint('已加载 ' + result.count + ' 张表情包');
          }
        } catch (error) {
          console.error('[MOSE] 表情包加载失败:', error);
        }
      },
      true
    );

    console.log('[MOSE] 表情包拦截器已就绪');
  }

  setupStickerInterceptor();
  console.log('[MOSE] Tauri bridge initialized (fetch→invoke + open + media + stickers)');
})();
