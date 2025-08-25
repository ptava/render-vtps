
"""Interactive camera setup and key bindings."""
from __future__ import annotations

from typing import Tuple

import paraview.simple as pv  # type: ignore[import-untyped]

from .pv_helpers import apply_coloring, discover_arrays


def _install_interactive_shortcuts(render_view) -> None:
    """Bind basic shortcuts on the interactor (e.g., 'r' => ResetCamera)."""
    iren = getattr(render_view, "GetInteractor", lambda: None)()
    if iren is None:
        return

    def _on_keypress(obj, _evt):
        try:
            key = obj.GetKeySym()
        except Exception:
            return
        if key in ("r", "R"):
            try:
                pv.ResetCamera(render_view)
                render_view.StillRender()
            except Exception:
                pass

    try:
        iren.AddObserver("KeyPressEvent", _on_keypress)
    except Exception:
        pass


def interactive_camera_setup(reader, render_view, display) -> Tuple[tuple, tuple, tuple, str | None]:
    """Enter interactive mode; allow field selection and return final camera."""
    print("Entering interactive mode. Adjust camera, then close the window to continue.")
    print(
        "\n"
        "Interactive tips:\n"
        "  • Drag to orbit/pan; scroll to zoom.\n"
        "  • Press 'r' to reset the camera to fit all visible data.\n"
        "  • Close the window to continue.\n"
    )

    _install_interactive_shortcuts(render_view)
    pv.Render()
    pv.Interact()

    camera_position = render_view.CameraPosition
    camera_focal_point = render_view.CameraFocalPoint
    camera_view_up = render_view.CameraViewUp

    point_arrays, cell_arrays = discover_arrays(reader)
    choices = [("POINTS", n) for n in point_arrays] + [("CELLS", n)
                                                       for n in cell_arrays]

    if choices:
        print("Available fields:")
        for i, (a, n) in enumerate(choices):
            print(f"  {i}: {n} [{a}]")
        try:
            field_choice = input(
                "Enter the number of the field to visualize (or press Enter to "
                "keep current): "
            ).strip()
            selected: str | None = None
            if field_choice.isdigit():
                idx = int(field_choice)
                if 0 <= idx < len(choices):
                    a, n = choices[idx]
                    apply_coloring(display, a, n)
                    selected = n
                    print(f"Selected field: {n} [{a}]")
                else:
                    print("Index out of range. Keeping current field.")
            elif field_choice:
                print("Unrecognized input. Keeping current field.")
        except EOFError:
            print("Input stream closed; keeping current field.")
    else:
        print("No fields available for interactive selection.")

    try:
        cam_vals = list(camera_position) + \
            list(camera_focal_point) + list(camera_view_up)
        cam_str = "[" + ",".join(f"{float(v):.9g}" for v in cam_vals) + "]"
        print("Reusable camera for future runs:")
        print(f"--camera_view_point '{cam_str}'")
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: could not format camera for reuse: {exc}")

    pv.Render()
    print("Exiting interactive mode.")
    return camera_position, camera_focal_point, camera_view_up, selected
