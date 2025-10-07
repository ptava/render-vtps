# animation.py
"""Animation export with fixed or over-time color scaling."""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import paraview.simple as pv

from .utils import parse_fixed_range, parse_render_size


def _determine_active_field(
    args,
    reader: object
) -> Tuple[Optional[str], Optional[str]]:
    """
    Return (assoc, name) for a *scalar* array only.

    Priority:
      --field if it exists and is scalar (POINTS or CELLS)
      first available scalar (POINTS preferred, else CELLS)
      (None, None) if no scalars found
    """
    pt_scalars, cl_scalars = [], []

    try:
        data = pv.servermanager.Fetch(reader)
        if data:
            point_data = data.GetPointData()
            cell_data = data.GetCellData()
            if point_data:
                for i in range(point_data.GetNumberOfArrays()):
                    arr = point_data.GetArray(i)
                    if arr and arr.GetNumberOfComponents() == 1:
                        pt_scalars.append(arr.GetName())
            if cell_data:
                for i in range(cell_data.GetNumberOfArrays()):
                    arr = cell_data.GetArray(i)
                    if arr and arr.GetNumberOfComponents() == 1:
                        cl_scalars.append(arr.GetName())
    except Exception:
        # If Fetch fails, we'll just return (None, None) below.
        pass

    field_arg = getattr(args, "field", None)
    if field_arg:
        if field_arg in pt_scalars:
            return "POINTS", field_arg
        if field_arg in cl_scalars:
            return "CELLS", field_arg
        print(
            f"[COLOR] Requested field '{field_arg}' is not a scalar or "
            "not available; ignoring."
        )

    if pt_scalars:
        return "POINTS", pt_scalars[0]
    if cl_scalars:
        return "CELLS", cl_scalars[0]

    return None, None

def generate_animation(
    args,
    readers: List[object],
    render_view: object,
    captured_camera: Optional[Dict]
) -> None:
    """Generate and save an animation with correct grid/edge updates."""
    os.makedirs(args.output_folder, exist_ok=True)
    out_base = os.path.join(args.output_folder, args.animation_filename)
    image_size = list(parse_render_size(args.render_size))
    movie_ext = args.output_format.lower()
    cmin, cmax = parse_fixed_range(args.range)

    # Dedicated export view; keep interactive view untouched
    export_view = pv.CreateView("RenderView")
    export_view.ViewSize = image_size

    # Copy camera/background from provided view or captured camera
    export_view.Background = list(render_view.Background)

    if captured_camera is not None:
        export_view.CameraPosition = captured_camera["CameraPosition"]
        export_view.CameraFocalPoint = captured_camera["CameraFocalPoint"]
        export_view.CameraViewUp = captured_camera["CameraViewUp"]
    else:
        export_view.CameraPosition = list(render_view.CameraPosition)
        export_view.CameraFocalPoint = list(render_view.CameraFocalPoint)
        export_view.CameraViewUp = list(render_view.CameraViewUp)

    export_view.CameraParallelScale = render_view.CameraParallelScale

    # Show all readers in the export view
    export_displays: List[object] = []
    for reader in readers:
        disp = pv.Show(reader, export_view)
        export_displays.append(disp)

    # Add time annotation
    annotate = pv.AnnotateTimeFilter(readers[0])
    annotate.Format = "t = {time:f}"
    ann_disp = pv.Show(annotate, export_view)
    ann_disp.FontSize = 14
    ann_disp.WindowLocation = args.time_location

    # Representation: ensure edges update correctly
    rep = getattr(args, "representation", None) or "Surface"
    for disp in export_displays:
        disp.SetRepresentationType(rep)
        if rep == "Surface With Edges":
            disp.EdgeColor = [0.0, 0.0, 0.0]

    pv.Render(export_view)

    # Determine active scalar to color by (optional)
    assoc, field = _determine_active_field(args, readers[0])

    if field:
        for disp in export_displays:
            pv.ColorBy(disp, (assoc, field))
        lut = pv.GetColorTransferFunction(field)
        pwf = pv.GetOpacityTransferFunction(field)
        export_displays[0].SetScalarBarVisibility(export_view, True)
        sb = pv.GetScalarBar(lut, export_view)
        sb.Title = field
        sb.ComponentTitle = ""
        sb.RangeLabelFormat = "%.6g"
    else:
        # Leave solid coloring; do not call ColorBy(..., None)
        print("[COLOR] No scalar field; using solid coloring.")
        lut = None
        pwf = None

    # Prepare time
    scene = pv.GetAnimationScene()
    scene.UpdateAnimationUsingDataTimeSteps()
    tvalues = list(scene.TimeKeeper.TimestepValues)
    if not tvalues:
        tvalues = [0.0]

    # Decide color range (only if a field is selected)
    if field:
        if (
            cmin is not None and cmax is not None and
            isinstance(cmin, (int, float)) and
            isinstance(cmax, (int, float)) and
            cmin < cmax
        ):
            lut.RescaleTransferFunction(float(cmin), float(cmax))
            pwf.RescaleTransferFunction(float(cmin), float(cmax))
        else:
            overall_min = float("inf")
            overall_max = float("-inf")

            for t in tvalues:
                for reader in readers:
                    pv.UpdatePipeline(time=float(t), proxy=reader)
                    data = pv.servermanager.Fetch(reader)
                    if data is None:
                        continue
                    if assoc == "POINTS":
                        arr = data.GetPointData().GetArray(field)
                    else:
                        arr = data.GetCellData().GetArray(field)
                    if arr is None:
                        continue
                    rng = arr.GetRange()
                    if rng and len(rng) >= 2:
                        overall_min = min(overall_min, float(rng[0]))
                        overall_max = max(overall_max, float(rng[1]))

            if overall_min < overall_max and overall_min < float("inf"):
                lut.RescaleTransferFunction(overall_min, overall_max)
                pwf.RescaleTransferFunction(overall_min, overall_max)

    # Activate the export view and save the animation
    pv.SetActiveView(export_view)
    frame_window = [0, max(0, len(tvalues) - 1)]
    movie_path = f"{out_base}.{movie_ext}"
    pv.SaveAnimation(
        movie_path,
        export_view,
        ImageResolution=image_size,
        FrameRate=args.fps,
        FrameWindow=frame_window
    )

