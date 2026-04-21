# animation.py
"""Animation export with fixed or over-time color scaling."""

from __future__ import annotations

import os
import shutil
from xml.sax.saxutils import escape
from typing import Dict, List, Optional, Tuple

import paraview.simple as pv

from .utils import (
    apply_background_color,
    apply_foreground_color,
    apply_scalar_bar_color,
    apply_text_color,
    parse_background_color,
    parse_fixed_range,
    parse_render_size,
)

FOREGROUND_COLOR = (0.0, 0.0, 0.0)


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

def _extract_time_values_from_reader(
        reader: object
) -> List[float]:
    file_names = getattr(reader, "FileNames", None)
    if not file_names:
        return []
    if isinstance(file_names, str):
        file_list = [file_names]
    else:
        file_list = list(file_names)

    time_values: List[float] = []
    for file_path in file_list:
        time_dir = os.path.basename(os.path.dirname(file_path))
        try:
            time_values.append(float(time_dir))
        except ValueError:
            continue
    return time_values

def _normalise_key_times(tvalues: List[float]) -> List[float]:
    span = max(tvalues) - min(tvalues)
    if span == 0.0:
        return [0.0 for _ in tvalues]
    return [(t - min(tvalues)) / span for t in tvalues]


def _surface_file_lists(readers: List[object], count: int) -> List[List[str]]:
    file_lists: List[List[str]] = []
    for reader in readers[:count]:
        file_names = getattr(reader, "FileNames", None)
        if not file_names:
            file_lists.append([])
        elif isinstance(file_names, str):
            file_lists.append([file_names])
        else:
            file_lists.append(list(file_names))
    return file_lists


def _safe_surface_name(file_list: List[str], index: int) -> str:
    stem = f"surface_{index + 1:02d}"
    if file_list:
        stem = os.path.splitext(os.path.basename(file_list[0]))[0]
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in stem)
    return safe


def _unique_surface_name(base_name: str, used_names: set[str]) -> str:
    name = base_name
    suffix = 2
    while name in used_names:
        name = f"{base_name}_{suffix:02d}"
        suffix += 1
    used_names.add(name)
    return name


def _link_or_copy(src: str, dst: str) -> None:
    if os.path.lexists(dst):
        os.remove(dst)
    try:
        target = os.path.relpath(os.path.abspath(src), start=os.path.dirname(dst))
        os.symlink(target, dst)
    except OSError:
        shutil.copy2(src, dst)


def _write_surface_collections(output_folder: str, readers: List[object], surface_count: int) -> None:
    collections_root = os.path.join(output_folder, "surface_collections")
    os.makedirs(collections_root, exist_ok=True)
    used_names: set[str] = set()

    for index, file_list in enumerate(_surface_file_lists(readers, surface_count)):
        if not file_list:
            continue

        surface_name = _unique_surface_name(
            _safe_surface_name(file_list, index),
            used_names,
        )
        surface_dir = os.path.join(
            collections_root,
            surface_name,
        )
        os.makedirs(surface_dir, exist_ok=True)

        datasets: List[Tuple[float, str]] = []
        for step, src in enumerate(file_list):
            try:
                timestep = float(os.path.basename(os.path.dirname(src)))
            except ValueError:
                timestep = float(step)
            ext = os.path.splitext(src)[1]
            local_name = f"{surface_name}_{step:06d}{ext}"
            local_path = os.path.join(surface_dir, local_name)
            _link_or_copy(src, local_path)
            datasets.append((timestep, local_name))

        pvd_path = os.path.join(surface_dir, "collection.pvd")
        with open(pvd_path, "w", encoding="utf-8") as handle:
            handle.write(
                "<?xml version=\"1.0\"?>\n"
                "<VTKFile type=\"Collection\" version=\"0.1\" byte_order=\"LittleEndian\">\n"
                "  <Collection>\n"
            )
            for timestep, src in datasets:
                handle.write(
                    f"    <DataSet timestep=\"{timestep:.16g}\" group=\"\" part=\"0\" file=\"{escape(src)}\"/>\n"
                )
            handle.write(
                "  </Collection>\n"
                "</VTKFile>\n"
            )

        print(f"[EXPORT] Wrote surface collection: {pvd_path}")

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
    surface_count = len(getattr(args, "source_representations", None) or [])

    if getattr(args, "collections", False):
        _write_surface_collections(args.output_folder, readers, surface_count)

    # Dedicated export view; keep interactive view untouched
    export_view = pv.CreateView("RenderView")
    export_view.ViewSize = image_size

    # Set export background explicitly so SaveAnimation uses the requested color.
    background = parse_background_color(getattr(args, "background", None))
    apply_background_color(export_view, background)
    apply_foreground_color(export_view, FOREGROUND_COLOR)

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

    # Representation: ensure edges update correctly
    source_representations = getattr(args, "source_representations", None) or []
    for index, disp in enumerate(export_displays):
        rep = source_representations[index] if index < len(source_representations) else "Surface"
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
        apply_scalar_bar_color(sb, FOREGROUND_COLOR)
    else:
        # Leave solid coloring; do not call ColorBy(..., None)
        print("[COLOR] No scalar field; using solid coloring.")
        lut = None
        pwf = None

    # Prepare time
    scene = pv.GetAnimationScene()
    scene.UpdateAnimationUsingDataTimeSteps()
    tvalues = list(scene.TimeKeeper.TimestepValues)

# --- extract time values safely ---
    reader_time_values = _extract_time_values_from_reader(readers[0])
    if reader_time_values:
        tvalues = [float(v) for v in reader_time_values]
    if not tvalues:
        tvalues = [0.0]

# --- annotation ---
    if reader_time_values:
        # Use a Text source, but update it via a PythonAnimationCue (not keyframes)
        text_source = pv.Text(registrationName="TimeLabel")
        text_source.Text = f"time = {tvalues[0]:g}"

        ann_disp = pv.Show(text_source, export_view)
        ann_disp.FontSize = 14
        ann_disp.WindowLocation = args.time_location
        apply_text_color(ann_disp, FOREGROUND_COLOR)

        scene = pv.GetAnimationScene()

        cue = pv.PythonAnimationCue()
        cue.StartTime = scene.StartTime
        cue.EndTime = scene.EndTime

        # Embed the time list directly into the cue script (runs in its own interpreter)
        cue.Script = f"""
from paraview.simple import FindSource, GetAnimationScene, Render

_times = {tvalues!r}  # your custom physical times, list of floats

def start_cue(cue):
    # initialize label at first value
    src = FindSource("TimeLabel")
    if src is not None and _times:
        src.Text = "time = %g" % float(_times[0])
        Render()

def tick(cue):
    scene = GetAnimationScene()
    tk = scene.TimeKeeper

    src = FindSource("TimeLabel")
    if src is None or not _times:
        return

    steps = list(getattr(tk, "TimestepValues", []) or [])

    if steps:
        # Map current dataset time -> nearest timestep index
        cur = float(tk.Time)
        i = min(range(len(steps)), key=lambda j: abs(float(steps[j]) - cur))
        # If counts differ, map index proportionally
        if len(_times) != len(steps) and len(steps) > 1 and len(_times) > 1:
            i = int(round(i * (len(_times) - 1) / (len(steps) - 1)))
    else:
        # Fallback: cue time is normalized in [0,1]
        at = float(cue.GetAnimationTime())
        i = int(round(at * (len(_times) - 1))) if len(_times) > 1 else 0

    i = max(0, min(i, len(_times) - 1))
    src.Text = "time = %g" % float(_times[i])
    Render()

def end_cue(cue):
    # optional: leave last value, or do nothing
    pass
"""

        scene.Cues.append(cue)

    else:
        annotate = pv.AnnotateTimeFilter(Input=readers[0])
        annotate.Format = "time = {time:f}"

        ann_disp = pv.Show(annotate, export_view)
        ann_disp.FontSize = 14
        ann_disp.WindowLocation = args.time_location
        apply_text_color(ann_disp, FOREGROUND_COLOR)

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
