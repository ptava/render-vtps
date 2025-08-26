"""Visualization pipeline setup."""
from __future__ import annotations

import os
from typing import List, Tuple

import paraview.simple as pv

from .pv_helpers import apply_coloring, discover_arrays, initialize_session
from .utils import parse_camera_view_point, parse_render_size


def pv_visualize(
    args,
    sources: List[Tuple[List[str], str]],
) -> Tuple[List[object], object, List[object]]:
    """Build the ParaView pipeline and return (readers, render_view, displays)."""
    initialize_session()

    render_view = pv.GetActiveViewOrCreate("RenderView")
    render_view.ViewSize = list(parse_render_size(args.render_size))

    bg = (args.background_color or "white").lower()
    if bg == "white":
        render_view.Background = [1.0, 1.0, 1.0]
    elif bg == "black":
        render_view.Background = [0.0, 0.0, 0.0]
    else:
        print(
            f"Warning: Unknown background color '{args.background_color}'. Using default white."
        )
        render_view.Background = [1.0, 1.0, 1.0]

    readers: List[object] = []
    displays: List[object] = []

    for time_dirs, selected_vtp_filename in sources:
        file_list: List[str] = []
        for td in time_dirs:
            fp = os.path.join(td, selected_vtp_filename)
            if os.path.exists(fp):
                file_list.append(fp)
        if not file_list:
            raise FileNotFoundError(
                "Selected VTP not found in any time directory after filtering."
            )

        reader = pv.OpenDataFile(file_list)
        display = pv.Show(reader, render_view)
        display.Representation = args.representation

        point_arrays, cell_arrays = discover_arrays(reader)

        assoc = None
        name = None
        if args.field:
            if args.field in point_arrays:
                assoc, name = "POINTS", args.field
            elif args.field in cell_arrays:
                assoc, name = "CELLS", args.field
            else:
                print(
                    "Warning: Field '%s' not found. Available: POINTS=%s, CELLS=%s. Falling back."
                    % (args.field, point_arrays, cell_arrays)
                )
        if name is None:
            if point_arrays:
                assoc, name = "POINTS", point_arrays[0]
            elif cell_arrays:
                assoc, name = "CELLS", cell_arrays[0]
            else:
                print("No fields available for visualization.")

        if name is not None:
            apply_coloring(display, assoc, name)  # type: ignore[arg-type]
        else:
            try:
                pv.ColorBy(display, None)
            except Exception:
                pass
            try:
                display.DiffuseColor = [0.8, 0.8, 0.8]
            except Exception:
                pass

        readers.append(reader)
        displays.append(display)

    stl_path = getattr(args, "stl_file", None)
    if stl_path:
        if os.path.exists(stl_path):
            stl_reader = pv.OpenDataFile(stl_path)
            stl_display = pv.Show(stl_reader, render_view)
            pv.ColorBy(stl_display, None)
            stl_display.DiffuseColor = [0.8, 0.8, 0.8]
            stl_display.Representation = 'Surface'
            readers.append(stl_reader)
            displays.append(stl_display)
        else:
            print(f"Warning: STL file '{stl_path}' not found. Skipping.")

    pv.ResetCamera(render_view)

    cam = parse_camera_view_point(getattr(args, "camera_view_point", None))
    if cam:
        pos, focal, up = cam
        render_view.CameraPosition = list(pos)
        render_view.CameraFocalPoint = list(focal)
        render_view.CameraViewUp = list(up)

    pv.Render()
    return readers, render_view, displays

