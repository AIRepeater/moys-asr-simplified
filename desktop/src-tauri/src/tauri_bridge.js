// MOSE Tauri Bridge：让 web/editor.js 不改一行就能在 Tauri 里跑。
//
// 做两件事：
// 1. Monkey-patch window.fetch：把 mose:// URL 重定向到 Tauri invoke（save/settings/recent）
// 2. 拦截"打开工程"按钮：用 Tauri dialog 选文件拿真实路径，再模拟 file input 给 editor.js
//
// 通过 Rust include_str! 嵌入到 index.html 的 </body> 前（editor.js 之后执行）。
(function () {
  'use strict';

  var invoke =
    (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) ||
    null;

  if (!invoke) {
    console.error('[MOSE] window.__TAURI__.core.invoke 不可用，IPC 功能无法工作');
    return;
  }

  // === 1. Monkey-patch fetch ===
  var originalFetch = window.fetch;

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

  window.fetch = async function (url, options) {
    options = options || {};
    var urlStr = String(url);
    var body = {};
    try {
      body = JSON.parse(options.body || '{}');
    } catch (e) {
      /* 非 JSON body，走原始 fetch */
    }

    try {
      if (urlStr.indexOf('mose://save-project') !== -1) {
        return okResponse(await invoke('save_project', body));
      }
      if (urlStr.indexOf('mose://recent-projects') !== -1) {
        return okResponse(await invoke('remember_project', body));
      }
      if (urlStr.indexOf('mose://settings') !== -1) {
        return okResponse(await invoke('update_settings', body));
      }
    } catch (error) {
      return errResponse(error);
    }

    return originalFetch.call(this, url, options);
  };

  // === 2. 拦截"打开工程"按钮 ===
  // editor.js 的 #open-project click 会触发 #open-project-file input click（浏览器拿不到路径）。
  // 这里在 capture 阶段拦截，改用 Tauri dialog 选文件（拿到真实路径），
  // 然后创建 File 对象模拟 file input change，让 editor.js 的 change handler 正常处理。

  function setupOpenProjectInterceptor() {
    var openBtn = document.getElementById('open-project');
    var fileInput = document.getElementById('open-project-file');
    if (!openBtn || !fileInput) {
      // editor.js 尚未执行完，延迟重试
      setTimeout(setupOpenProjectInterceptor, 50);
      return;
    }

    openBtn.addEventListener(
      'click',
      async function (e) {
        e.stopImmediatePropagation(); // 阻止 editor.js 的 click handler

        try {
          var result = await invoke('open_project');
          if (!result || !result.ok || result.cancelled) return;

          // 用返回的工程数据创建 File 对象，模拟 file input
          var jsonContent = JSON.stringify(result.data);
          var file = new File([jsonContent], result.filename || 'untitled.json', {
            type: 'application/json',
          });
          var dt = new DataTransfer();
          dt.items.add(file);
          fileInput.files = dt.files;
          fileInput.dispatchEvent(new Event('change', { bubbles: true }));

          // 打开工程成功后，启用"保存工程"按钮
          if (typeof SERVER_CONFIG !== 'undefined') {
            SERVER_CONFIG.canSave = true;
          }
          var saveDropdown = document.getElementById('save-project-dropdown');
          if (saveDropdown) saveDropdown.hidden = false;
        } catch (error) {
          console.error('[MOSE] 打开工程失败:', error);
        }
      },
      true // capture 阶段，确保在 editor.js 之前
    );

    console.log('[MOSE] "打开工程"拦截器已就绪');
  }

  setupOpenProjectInterceptor();
  console.log('[MOSE] Tauri bridge initialized (fetch→invoke + open_project)');
})();
