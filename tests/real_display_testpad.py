"""Tiny X11 target app for the opt-in real-display desktop-control test.

Uses python-xlib only (no tkinter).  Window title "Aureon Test Pad", a button
and a text box.  Every change is mirrored to a JSON state file so the test can
read back exactly what the desktop layer did.  Not a test module itself.

    python tests/real_display_testpad.py STATE_JSON
"""

from __future__ import annotations

import json
import os
import sys

from Xlib import XK, X, Xatom, display

TITLE = "Aureon Test Pad"
WIDTH, HEIGHT = 600, 260
BUTTON = (40, 40, 180, 50)  # x, y, w, h relative to the window
BOX = (40, 130, 520, 40)


def main(state_path: str) -> int:
    d = display.Display()
    screen = d.screen()
    window = screen.root.create_window(
        100, 100, WIDTH, HEIGHT, 0, screen.root_depth, X.InputOutput, X.CopyFromParent,
        background_pixel=screen.white_pixel,
        event_mask=X.ExposureMask | X.ButtonPressMask | X.KeyPressMask | X.StructureNotifyMask,
    )
    window.set_wm_name(TITLE)
    window.change_property(d.intern_atom("_NET_WM_NAME"), d.intern_atom("UTF8_STRING"), 8, TITLE.encode())
    window.change_property(d.intern_atom("_NET_WM_PID"), Xatom.CARDINAL, 32, [os.getpid()])
    font = d.open_font("fixed")
    ink = window.create_gc(foreground=screen.black_pixel, background=screen.white_pixel, font=font)
    blue = window.create_gc(foreground=0x3366CC, background=screen.white_pixel)
    white = window.create_gc(foreground=screen.white_pixel, background=0x3366CC, font=font)
    state: dict = {"clicks": 0, "text": "", "submitted": [], "box_focused": False,
                   "pid": os.getpid(), "window_id": window.id, "ready": False}

    def save() -> None:
        tmp = state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        os.replace(tmp, state_path)

    def draw() -> None:
        window.clear_area()
        window.fill_rectangle(blue, *BUTTON)
        window.draw_text(white, BUTTON[0] + 20, BUTTON[1] + 30, f"Click me ({state['clicks']})".encode())
        window.rectangle(ink, *BOX)
        caret = "|" if state["box_focused"] else ""
        window.draw_text(ink, BOX[0] + 8, BOX[1] + 25, (state["text"] + caret).encode())
        window.draw_text(ink, 40, 220, f"submitted: {state['submitted'][-1:]}".encode())
        d.flush()

    def inside(rect: tuple, x: int, y: int) -> bool:
        return rect[0] <= x < rect[0] + rect[2] and rect[1] <= y < rect[1] + rect[3]

    window.map()
    d.sync()
    while True:
        event = d.next_event()
        if event.type == X.MapNotify:
            window.set_input_focus(X.RevertToParent, X.CurrentTime)
            origin = window.translate_coords(screen.root, 0, 0)
            state["origin"] = [-origin.x, -origin.y]
            state["button_center"] = [-origin.x + BUTTON[0] + BUTTON[2] // 2, -origin.y + BUTTON[1] + BUTTON[3] // 2]
            state["box_center"] = [-origin.x + BOX[0] + BOX[2] // 2, -origin.y + BOX[1] + BOX[3] // 2]
            state["ready"] = True
            d.sync()
            save()
        elif event.type == X.Expose:
            draw()
        elif event.type == X.ButtonPress:
            if inside(BUTTON, event.event_x, event.event_y):
                state["clicks"] += 1
            elif inside(BOX, event.event_x, event.event_y):
                state["box_focused"] = True
            else:
                state["box_focused"] = False
            save()
            draw()
        elif event.type == X.KeyPress and state["box_focused"]:
            keysym = d.keycode_to_keysym(event.detail, 1 if event.state & X.ShiftMask else 0)
            if keysym == XK.XK_BackSpace:
                state["text"] = state["text"][:-1]
            elif keysym in (XK.XK_Return, XK.XK_KP_Enter):
                state["submitted"].append(state["text"])
            elif keysym == XK.XK_space:
                state["text"] += " "
            else:
                name = XK.keysym_to_string(keysym)
                if name and len(name) == 1 and name.isalnum():
                    state["text"] += name
            save()
            draw()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
