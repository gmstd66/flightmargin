from app.adapters.codex_stdio import (
    CodexAppServer,
    resolve_windows_npm_codex,
    windows_hidden_subprocess_kwargs,
)


def test_windows_subprocess_configuration_is_empty_off_windows():
    assert windows_hidden_subprocess_kwargs(system_name="posix") == {}


def test_windows_subprocess_configuration_requests_hidden_console(monkeypatch):
    import app.adapters.codex_stdio as module

    class Startup:
        def __init__(self):
            self.dwFlags = 0
            self.wShowWindow = None

    monkeypatch.setattr(module.subprocess, "STARTUPINFO", Startup, raising=False)
    monkeypatch.setattr(module.subprocess, "STARTF_USESHOWWINDOW", 1, raising=False)
    monkeypatch.setattr(module.subprocess, "SW_HIDE", 0, raising=False)
    monkeypatch.setattr(module.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    result = module.windows_hidden_subprocess_kwargs(system_name="nt")
    assert result["creationflags"] == 0x08000000
    assert result["startupinfo"].wShowWindow == 0


def test_official_windows_npm_shim_resolves_to_native_binary(tmp_path):
    npm = tmp_path / "npm"
    wrapper = npm / "codex.CMD"
    package = npm / "node_modules" / "@openai" / "codex"
    native = (
        package
        / "node_modules"
        / "@openai"
        / "codex-win32-x64"
        / "vendor"
        / "x86_64-pc-windows-msvc"
        / "bin"
        / "codex.exe"
    )
    (package / "bin").mkdir(parents=True)
    (package / "bin" / "codex.js").touch()
    native.parent.mkdir(parents=True)
    native.touch()
    wrapper.touch()

    assert resolve_windows_npm_codex(
        str(wrapper),
        system_name="nt",
        machine="AMD64",
    ) == str(native)


def test_unrecognized_windows_codex_layout_keeps_wrapper(tmp_path):
    wrapper = tmp_path / "codex.cmd"
    wrapper.touch()

    assert resolve_windows_npm_codex(
        str(wrapper),
        system_name="nt",
        machine="AMD64",
    ) == str(wrapper)


def test_explicit_codex_override_is_not_rewritten(monkeypatch, tmp_path):
    wrapper = tmp_path / "codex.cmd"
    wrapper.touch()
    monkeypatch.setattr(
        "app.adapters.codex_stdio.resolve_windows_npm_codex",
        lambda _value: "unexpected",
    )

    assert CodexAppServer(executable=str(wrapper)).executable == str(wrapper)
