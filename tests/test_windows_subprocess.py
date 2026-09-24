from app.adapters.codex_stdio import windows_hidden_subprocess_kwargs


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
