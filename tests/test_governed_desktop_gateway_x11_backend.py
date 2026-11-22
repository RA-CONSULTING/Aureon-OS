"""The governed gateway must be able to identify the foreground window on X11.

On main the only backend is ``LazyPyAutoGUIBackend``, whose
``foreground_window`` calls ``ctypes.windll`` and therefore always fails on
Linux: ``bind_target_window`` raised ``foreground_window_query_failed`` and the
gateway could neither observe nor act on any X11 display.  These tests use a
stand-in ``Xlib`` module, so they need no display.
"""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

from aureon.autonomous import aureon_governed_desktop_gateway as gw


class _Prop:
    def __init__(self, value):
        self.value = value


class _Win:
    def __init__(self, wid, *, parent=None, props=None, geom=(0, 0, 10, 10), origin=(0, 0)):
        self.id = wid
        self._parent = parent
        self._props = props or {}
        self._geom = geom
        self._origin = origin

    def query_tree(self):
        return SimpleNamespace(parent=self._parent)

    def get_full_property(self, atom, _type):
        value = self._props.get(atom)
        return None if value is None else _Prop(value)

    def get_wm_name(self):
        return self._props.get("WM_NAME")

    def get_geometry(self):
        x, y, w, h = self._geom
        return SimpleNamespace(x=x, y=y, width=w, height=h)

    def translate_coords(self, _root, x, y):
        # Xlib returns the root's coordinates relative to this window.
        return SimpleNamespace(x=-self._origin[0] + x, y=-self._origin[1] + y)


class _Display:
    def __init__(self, root, *, focus, windows):
        self._root = root
        self._focus = focus
        self._windows = windows

    def screen(self):
        return SimpleNamespace(root=self._root, width_in_pixels=1280, height_in_pixels=800)

    def intern_atom(self, name):
        return name

    def get_input_focus(self):
        return SimpleNamespace(focus=self._focus)

    def create_resource_object(self, _kind, wid):
        return self._windows[wid]


def _install_fake_xlib(monkeypatch, display_obj):
    xlib = types.ModuleType("Xlib")
    xdisplay = types.ModuleType("Xlib.display")
    xdisplay.Display = lambda _name=None: display_obj
    xlib.display = xdisplay
    monkeypatch.setitem(sys.modules, "Xlib", xlib)
    monkeypatch.setitem(sys.modules, "Xlib.display", xdisplay)


def test_default_backend_on_linux_with_display_is_x11(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":42")
    assert isinstance(gw.default_desktop_backend(), gw.X11PyAutoGUIBackend)
    assert isinstance(gw.GovernedDesktopGateway()._backend, gw.X11PyAutoGUIBackend)


def test_default_backend_on_windows_stays_win32(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    backend = gw.default_desktop_backend()
    assert type(backend) is gw.LazyPyAutoGUIBackend


def test_x11_foreground_window_reads_focused_client_without_wm(monkeypatch) -> None:
    root = _Win(1)
    app = _Win(
        0x200000,
        parent=root,
        props={"_NET_WM_PID": [4242], "_NET_WM_NAME": b"Aureon Test Pad"},
        geom=(0, 0, 600, 260),
        origin=(100, 100),
    )
    child = _Win(0x200001, parent=app)
    _install_fake_xlib(monkeypatch, _Display(root, focus=child, windows={}))

    info = gw.X11PyAutoGUIBackend().foreground_window()

    assert info == gw.WindowInfo(
        handle=0x200000, title="Aureon Test Pad", process_id=4242, left=100, top=100, width=600, height=260
    )


def test_x11_foreground_window_prefers_net_active_window(monkeypatch) -> None:
    frame = _Win(5, parent=None)
    root = _Win(1, props={"_NET_ACTIVE_WINDOW": [0x300000]})
    frame._parent = root
    client = _Win(
        0x300000,
        parent=frame,
        props={"_NET_WM_PID": [77], "_NET_WM_NAME": "Editor"},
        geom=(0, 0, 300, 200),
        origin=(10, 30),
    )
    _install_fake_xlib(monkeypatch, _Display(root, focus=None, windows={0x300000: client}))

    info = gw.X11PyAutoGUIBackend().foreground_window()

    assert (info.handle, info.process_id, info.title, info.left, info.top) == (0x300000, 77, "Editor", 10, 30)


def test_x11_foreground_window_without_pid_fails_closed(monkeypatch) -> None:
    root = _Win(1)
    app = _Win(9, parent=root, props={"_NET_WM_NAME": b"No pid"})
    _install_fake_xlib(monkeypatch, _Display(root, focus=app, windows={}))

    with pytest.raises(gw.DesktopBackendError, match="foreground_window_pid_unavailable"):
        gw.X11PyAutoGUIBackend().foreground_window()


def test_x11_no_focus_fails_closed(monkeypatch) -> None:
    root = _Win(1)
    _install_fake_xlib(monkeypatch, _Display(root, focus=1, windows={}))  # PointerRoot

    with pytest.raises(gw.DesktopBackendError, match="foreground_window_unavailable"):
        gw.X11PyAutoGUIBackend().foreground_window()


def test_x11_gateway_rejects_pid_mismatch(monkeypatch, tmp_path) -> None:
    root = _Win(1)
    app = _Win(
        0x200000,
        parent=root,
        props={"_NET_WM_PID": [4242], "_NET_WM_NAME": b"Aureon Test Pad"},
        geom=(0, 0, 600, 260),
        origin=(100, 100),
    )
    _install_fake_xlib(monkeypatch, _Display(root, focus=app, windows={}))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":42")
    gateway = gw.GovernedDesktopGateway(evidence_path=tmp_path / "evidence.jsonl")

    with pytest.raises(gw.DesktopGatewayError, match="target_window_process_mismatch"):
        gateway.bind_target_window("Aureon Test Pad", expected_process_id=9999)

    assert gateway.status()["binding_count"] == 0


def test_x11_empty_screenshot_bytes_are_not_success(monkeypatch) -> None:
    class _EmptyImage:
        def save(self, buffer, format=None):
            return None

    imagegrab = types.ModuleType("PIL.ImageGrab")
    imagegrab.grab = lambda *_args, **_kwargs: _EmptyImage()
    pil = types.ModuleType("PIL")
    pil.ImageGrab = imagegrab
    monkeypatch.setitem(sys.modules, "PIL", pil)
    monkeypatch.setitem(sys.modules, "PIL.ImageGrab", imagegrab)

    with pytest.raises(gw.DesktopBackendError, match="empty_screen_capture"):
        gw.X11PyAutoGUIBackend().capture_screen()


def test_x11_without_xlib_fails_closed(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "Xlib", None)
    monkeypatch.delitem(sys.modules, "Xlib.display", raising=False)

    with pytest.raises(gw.DesktopBackendError, match="x11_display_unavailable"):
        gw.X11PyAutoGUIBackend().screen_size()


def test_x11_gateway_binds_window_through_default_backend(monkeypatch, tmp_path) -> None:
    root = _Win(1)
    app = _Win(
        0x200000,
        parent=root,
        props={"_NET_WM_PID": [4242], "_NET_WM_NAME": b"Aureon Test Pad"},
        geom=(0, 0, 600, 260),
        origin=(100, 100),
    )
    _install_fake_xlib(monkeypatch, _Display(root, focus=app, windows={}))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":42")
    gateway = gw.GovernedDesktopGateway(evidence_path=tmp_path / "evidence.jsonl")

    binding = gateway.bind_target_window("Aureon Test Pad", expected_process_id=4242)

    assert (binding.handle, binding.process_id) == (0x200000, 4242)


def test_constructing_x11_backend_touches_nothing(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "Xlib", raising=False)
    monkeypatch.delitem(sys.modules, "Xlib.display", raising=False)
    gw.X11PyAutoGUIBackend()
    assert "Xlib.display" not in sys.modules
