from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class PackagingContractTests(unittest.TestCase):
    def test_launcher_version_matches_project_metadata(self) -> None:
        """Given project metadata, When the Launcher is packaged, Then every displayed fallback version matches it."""
        project = tomllib.loads(read_text("pyproject.toml"))
        version = project["project"]["version"]
        launcher_html = read_text("web/launcher/index.html")
        launcher_js = read_text("web/launcher/launcher.js")
        gui = read_text("maw/gui_web.py")

        self.assertIn(f'id="appVersion">v{version}</span>', launcher_html)
        self.assertIn(f'appVersion: "{version}"', launcher_js)
        self.assertIn(f'BUNDLED_APP_VERSION = "{version}"', gui)

    def test_pyinstaller_build_dependency_is_locked_outside_runtime_dependencies(self) -> None:
        """Given packaging needs PyInstaller, When metadata is read, Then build deps stay in the build group."""
        pyproject = read_text("pyproject.toml")

        self.assertIsNone(re.search(r'(?s)dependencies = \[[^\]]*"pyinstaller', pyproject))
        self.assertRegex(pyproject, r'(?s)\[dependency-groups\].*build = \[[^\]]*"pyinstaller==6\.16\.0"')

    def test_runtime_dependencies_are_pinned_for_reproducible_builds(self) -> None:
        """Given releases must stay reproducible without a lockfile, When metadata is read, Then runtime deps are exact pins."""
        project = tomllib.loads(read_text("pyproject.toml"))

        for requirement in project["project"]["dependencies"]:
            name_and_spec = requirement.split(";")[0]
            self.assertIn("==", name_and_spec, requirement)

    def test_gitignore_keeps_local_windows_bundle_and_generated_build_state_untracked(self) -> None:
        """Given local EXE builds are retained, When ignore rules are read, Then binaries stay local."""
        ignored_paths = set(read_text(".gitignore").splitlines())

        self.assertIn("/dist/", ignored_paths)
        self.assertIn("/build/", ignored_paths)
        self.assertIn("*.spec.bak", ignored_paths)
        self.assertIn("*.exe", ignored_paths)
        self.assertIn("!MAW.spec", ignored_paths)
        self.assertIn("/dist/MAW/MAW.exe", ignored_paths)

    def test_spec_packages_qwen_only_gui_bundle(self) -> None:
        """Given the trimmed GUI bundle, When MAW.spec is read, Then it is onedir/windowed/noupx with only kept modules."""
        spec = read_text("MAW.spec")

        self.assertIn("maw_gui.py", spec)
        self.assertIn("name='MAW'", spec)
        self.assertIn("console=False", spec)
        self.assertIn("upx=False", spec)
        self.assertIn('"maw.console"', spec)
        self.assertIn("pyinstaller_utf8.py", spec)
        self.assertIn('"maw.gui_web"', spec)
        self.assertIn('"maw.gui_workflow"', spec)
        self.assertIn('"maw.gui_config"', spec)
        self.assertIn('"maw.launcher_batch"', spec)
        self.assertIn('"maw.qwen_audio"', spec)
        self.assertIn('"maw.segments"', spec)
        self.assertIn('"maw.speaker"', spec)
        self.assertIn("generate_subtitle_qwen_api", spec)
        self.assertIn('binaries=binaries', spec)
        self.assertIn("binaries = []", spec)
        self.assertIn("assets", spec)
        self.assertIn("maw.ico", spec)
        self.assertIn("show.webp", spec)
        self.assertIn("icon=str(ROOT / 'assets' / 'maw.ico')", spec)
        self.assertIn("COLLECT(", spec)
        self.assertNotIn("onefile=True", spec)
        for bundled_path in ("web", "LICENSE", "THIRD_PARTY_NOTICES.md"):
            self.assertIn(bundled_path, spec)
        # 已删功能不得再出现在打包契约里。
        for removed in (
            "maw.cli",
            "maw.soniox",
            "maw.bcut",
            "maw.local_runtime",
            "maw.local_models",
            "maw.local_asr",
            "maw.ocr_runtime",
            "maw.postprocess",
            "maw.project",
            "maw.waveform",
            "maw.media_cache",
            "maw.text_conversion",
            "generate_subtitle_soniox_api",
            "generate_subtitle_bcut_api",
            "generate_subtitle_local",
            "server-editor",
            "blank-editor",
            "local-runtime",
            "ocr-runtime",
            "opencc",
            "reapeaks",
        ):
            self.assertNotIn(removed, spec)
        self.assertIn("excludes=[]", spec)
        faq_path = ROOT / "FAQ-常见问题.txt"
        self.assertTrue(faq_path.is_file())
        self.assertIn("FAQ-常见问题.txt", spec)
        self.assertNotIn('"*.mp4"', spec)
        self.assertNotIn('"*.srt"', spec)

    def test_macos_bundle_uses_the_icns_app_icon(self) -> None:
        """Given a macOS app bundle, When PyInstaller builds it, Then the bundle has the branded ICNS icon."""
        spec = read_text("MAW.spec")
        workflow = read_text(".github/workflows/release.yml")
        icon = (ROOT / "assets" / "maw.icns").read_bytes()

        self.assertIn("icon=str(ROOT / 'assets' / 'maw.icns')", spec)
        self.assertNotIn("icon=None", spec)
        self.assertIn("scripts/build_macos_icon.py --check", workflow)
        self.assertTrue(icon.startswith(b"icns"))
        self.assertEqual(int.from_bytes(icon[4:8], "big"), len(icon))
        self.assertIn(b"ic07", icon)
        self.assertIn(b"ic08", icon)

    def test_macos_release_workflow_publishes_maw_archives_without_mose_or_checksums(self) -> None:
        """Given a macOS arm64 release, When packaging runs, Then only MAW app variants are uploaded."""
        workflow = read_text(".github/workflows/release.yml")

        self.assertIn("os: macos-14", workflow)
        self.assertIn("arch: arm64", workflow)
        self.assertIn("https://www.osxexperts.net/ffmpeg81arm.zip", workflow)
        self.assertIn("https://www.osxexperts.net/ffprobe81arm.zip", workflow)
        self.assertNotIn("MOSE", workflow)
        self.assertNotIn("actions/setup-node@v4", workflow)
        self.assertNotIn("dtolnay/rust-toolchain@stable", workflow)
        self.assertNotIn("cargo check --manifest-path src-tauri/Cargo.toml", workflow)

    def test_tag_release_workflows_use_idempotent_release_uploads(self) -> None:
        """Given the merged release workflow publishes one tag release, When it runs, Then it uses idempotent gh CLI uploads."""
        workflow = read_text(".github/workflows/release.yml")
        self.assertIn("gh release upload", workflow)
        self.assertIn("--clobber", workflow)
        self.assertIn("scripts/prepare_release_notes.py", workflow)
        self.assertIn("gh release edit", workflow)
        self.assertIn("--notes-file release-notes.md", workflow)
        # publish 必须同时满足 tag 触发 + Windows 构建成功，否则 dispatch 会误发 Release
        self.assertIn("startsWith(github.ref, 'refs/tags/v') && !cancelled() && needs.build-windows.result == 'success'", workflow)
        # 不完整构建警告：needs 上下文只提供单数 result（矩阵 job 的聚合结果），
        # 复数 results 不是有效属性，会让警告永不触发
        self.assertIn("needs.build-aux.result == 'failure'", workflow)
        self.assertNotIn("needs.build-aux.results", workflow)
        # macOS-specific assertions
        self.assertNotIn("tauri.macos.conf.json", workflow)
        self.assertIn("ebb82529562b71170807bbc6b0e7eb4f0b13af8cbb0e085bb9e8f6fe709598ad", workflow)
        self.assertIn("a6640a77d38a6f0527c5b597e599cb36a3427a6931444ed80bc62542421950a1", workflow)
        self.assertIn("MAW.app/Contents/MacOS/ffmpeg/bin", workflow)
        self.assertIn("codesign --force --deep --sign - dist/MAW.app", workflow)
        self.assertIn("MAW-macOS-arm64-${Version}.zip", workflow)
        self.assertIn("MAW-lite-macOS-arm64-${Version}.zip", workflow)
        self.assertIn("scripts/sync_launcher_version.py --write", workflow)
        self.assertIn("scripts/sync_launcher_version.py --check", workflow)
        self.assertIn('StandardStage="build/release/standard"', workflow)
        self.assertIn('LiteStage="build/release/lite"', workflow)
        self.assertIn('zip -qry "$GITHUB_WORKSPACE/$StandardArchive" MAW.app', workflow)
        self.assertIn('zip -qry "$GITHUB_WORKSPACE/$LiteArchive" MAW-lite.app', workflow)
        self.assertIn('FAQ-常见问题.txt', workflow)
        self.assertNotIn("MOSE.app", workflow)
        self.assertIn("MAW-lite-macOS-arm64-*.zip", workflow)
        self.assertNotIn(".zip.sha256", workflow)

    def test_appimage_build_drops_bundled_cpp_runtime(self) -> None:
        """Given the AppImage build script and workflow, When the AppDir is assembled, Then bundled libstdc++/libgcc_s/libgbm are removed and CI forbids them."""
        script = read_text("scripts/build-appimage.sh")
        workflow = read_text(".github/workflows/release.yml")

        self.assertIn('rm -f "$APP_DIR/_internal/libstdc++.so.6" "$APP_DIR/_internal/libgcc_s.so.1"', script)
        self.assertIn('"$APP_DIR/_internal/libgbm.so.1"', script)
        self.assertIn("Verify no bundled C++ runtime in AppImage", workflow)
        self.assertIn("_internal/libgbm.so.1", workflow)

    def test_appimage_build_ships_ffmpeg_gpl_license_and_source_notice(self) -> None:
        """Given the AppImage build script, When the BtbN GPL ffmpeg build is bundled, Then the GPLv3 license text and a source notice are written into the bundle."""
        script = read_text("scripts/build-appimage.sh")

        self.assertIn('cp "FAQ-常见问题.txt" "dist/MAW/FAQ-常见问题.txt"', script)
        self.assertIn('dist/MAW/ffmpeg/GPLv3.txt', script)
        self.assertIn('dist/MAW/ffmpeg/SOURCE.txt', script)
        self.assertIn('https://www.gnu.org/licenses/gpl-3.0.txt', script)
        self.assertIn('Build provider: https://github.com/BtbN/FFmpeg-Builds', script)
        self.assertIn('Archive SHA-256: $FFMPEG_SHA256', script)

    def test_local_build_script_invokes_uv_and_pyinstaller_for_maw_onedir(self) -> None:
        """Given a Windows developer build, When the script is read, Then it builds dist/MAW/MAW.exe."""
        script = read_text("scripts/build-windows.ps1")

        self.assertIn("uv sync --group build", script)
        self.assertNotIn("--frozen", script)
        self.assertIn("uv run --group build pyinstaller", script)
        self.assertIn("MAW.spec", script)
        self.assertIn("dist\\MAW\\MAW.exe", script)
        self.assertIn("$FaqSource", script)
        self.assertIn("$FaqBundlePath", script)
        self.assertNotIn("cargo check --manifest-path", script)
        self.assertNotIn("npm run tauri -- build", script)
        self.assertNotIn("MOSE", script)
        self.assertNotIn("bootstrap", script)
        self.assertIn("$ErrorActionPreference = 'Stop'", script)

    def test_windows_preview_workflow_verifies_launcher_version(self) -> None:
        """Given a Windows preview build, When packaging starts, Then stale Launcher versions fail early."""
        workflow = read_text(".github/workflows/pr-release-windows.yml")

        self.assertIn("scripts/sync_launcher_version.py --check", workflow)

    def test_release_workflow_is_tag_triggered_and_publishes_both_windows_packages(self) -> None:
        """Given a v* tag push, When workflow is read, Then it releases MAW and MAW-lite builds."""
        workflow = read_text(".github/workflows/release.yml")

        self.assertRegex(workflow, re.compile(r"on:\s+push:\s+tags:\s+- 'v\*'", re.MULTILINE))
        self.assertIn("windows-2022", workflow)
        self.assertNotIn("actions/setup-node@v4", workflow)
        self.assertNotIn("dtolnay/rust-toolchain@stable", workflow)
        self.assertIn("uv sync --group build", workflow)
        self.assertNotIn("--frozen", workflow)
        self.assertIn("tests/test_packaging_contract.py", workflow)
        self.assertIn("pyproject.toml", workflow)
        self.assertIn("github.ref_name", workflow)
        self.assertIn(r's/^version = "\(.*\)"$/\1/p', workflow)
        self.assertIn("scripts/sync_launcher_version.py --write", workflow)
        self.assertIn("scripts/sync_launcher_version.py --check", workflow)
        self.assertIn("PYTHONUTF8: '1'", workflow)
        self.assertIn("dist\\MAW\\MAW.exe", workflow)
        self.assertNotIn("MOSE", workflow)
        self.assertIn("Compress-Archive", workflow)
        self.assertIn("Get-FileHash", workflow)
        self.assertIn("$FfmpegVersion = '8.1.2'", workflow)
        self.assertIn("ffmpeg-$FfmpegVersion-essentials_build.zip", workflow)
        self.assertIn("https://github.com/GyanD/codexffmpeg/releases/download", workflow)
        self.assertIn("for ($attempt = 1; $attempt -le 3; $attempt++)", workflow)
        self.assertIn("Start-Sleep -Seconds 10", workflow)
        self.assertIn("$DownloadedUrl", workflow)
        self.assertIn("db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec", workflow)
        self.assertIn("ffmpeg.exe", workflow)
        self.assertIn("ffprobe.exe", workflow)
        self.assertNotIn("ffplay.exe", workflow)
        self.assertIn("MAW-Windows-x64-${{ steps.version.outputs.version }}.zip", workflow)
        self.assertIn("MAW-lite-Windows-x64-${{ steps.version.outputs.version }}.zip", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("gh release upload", workflow)
        self.assertIn("--target '${{ github.sha }}'", workflow)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", workflow)
        self.assertNotIn(".zip.sha256", workflow)

    def test_pr_release_workflow_builds_only_the_no_ffmpeg_windows_preview(self) -> None:
        """Given a pull request, When packaging runs, Then only a read-only standard ZIP is uploaded."""
        workflow = read_text(".github/workflows/pr-release-windows.yml")

        self.assertRegex(workflow, re.compile(r"on:\s+pull_request:", re.MULTILINE))
        self.assertRegex(workflow, re.compile(r"push:\s+branches-ignore: \[main\]", re.MULTILINE))
        self.assertIn("windows-2022", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertNotIn("actions/setup-node@v4", workflow)
        self.assertNotIn("dtolnay/rust-toolchain@stable", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.head.sha || github.sha }}", workflow)
        self.assertIn("uv sync --group build", workflow)
        self.assertNotIn("--frozen", workflow)
        self.assertIn("scripts\\build-windows.ps1 -SkipTests", workflow)
        self.assertIn("dist\\MAW\\MAW.exe", workflow)
        self.assertNotIn("MOSE", workflow)
        self.assertIn("Verify no FFmpeg is bundled", workflow)
        self.assertIn("Compress-Archive", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("retention-days: 14", workflow)
        self.assertIn("MAW-lite-Windows-x64-pr-", workflow)
        self.assertNotIn(".zip.sha256", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("MAWxFF", workflow)
        self.assertNotIn("softprops/action-gh-release", workflow)

    def test_pr_release_comment_workflow_updates_the_pr_with_the_run_link(self) -> None:
        """Given a completed PR package run, When the comment workflow runs, Then it updates one PR comment."""
        workflow = read_text(".github/workflows/pr-release-comment.yml")

        self.assertIn("workflow_run:", workflow)
        self.assertIn("workflows: [Preview Windows Release]", workflow)
        self.assertIn("types: [completed]", workflow)
        self.assertIn("pull-requests: write", workflow)
        self.assertIn("actions/github-script@v7", workflow)
        self.assertIn("maw-windows-pr-release", workflow)
        self.assertIn("issues.updateComment", workflow)
        self.assertIn("issues.createComment", workflow)
        self.assertIn("run.html_url", workflow)


if __name__ == "__main__":
    _ = unittest.main()
