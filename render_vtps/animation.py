
"""Animation export with fixed or per-frame color scaling."""
from __future__ import annotations

import os
from typing import Tuple, Optional, Dict, List

import paraview.simple as pv

from .utils import parse_fixed_range, parse_render_size


def _determine_active_field(args, reader) -> Tuple[Optional[str], Optional[str]]:
    """
    Return (assoc, name) for a *scalar* array only.
    Priority:
      --field if it exists and is scalar (POINTS or CELLS)
      first available scalar (POINTS preferred, else CELLS)
      (None, None) if no scalars found
    """
    import paraview.simple as pv

    pt_scalars, cl_scalars = [], []

    try:
        data = pv.servermanager.Fetch(reader)
        if data:
            pd, cd = data.GetPointData(), data.GetCellData()
            if pd:
                for i in range(pd.GetNumberOfArrays()):
                    arr = pd.GetArray(i)
                    if arr and arr.GetNumberOfComponents() == 1:
                        pt_scalars.append(arr.GetName())
            if cd:
                for i in range(cd.GetNumberOfArrays()):
                    arr = cd.GetArray(i)
                    if arr and arr.GetNumberOfComponents() == 1:
                        cl_scalars.append(arr.GetName())
    except Exception:
        # if Fetch fails, we’ll just return (None, None) below
        pass

    fld = getattr(args, "field", None)
    if fld:
        if fld in pt_scalars:
            return "POINTS", fld
        if fld in cl_scalars:
            return "CELLS", fld
        print(
            f"[COLOR] Requested field '{fld}' is not a scalar or not available; ignoring.")

    if pt_scalars:
        return "POINTS", pt_scalars[0]
    if cl_scalars:
        return "CELLS", cl_scalars[0]

    return None, None


def generate_animation(
        args,
        readers: List[object],
        render_view,
        captured_camera: Optional[Dict]) -> None:
    os.makedirs(args.output_folder, exist_ok=True)
    out_base = os.path.join(args.output_folder, args.animation_filename)
    res = list(parse_render_size(args.render_size))
    movie_ext = args.output_format.lower()
    cmin, cmax = parse_fixed_range(args.range)

    export_view = pv.CreateView("RenderView")
    export_view.ViewSize = res
    for attr in ("UseOffscreenRenderingForScreenshots", "UseOffscreenRendering"):
        try:
            if hasattr(export_view, attr):
                setattr(export_view, attr, 1)
        except Exception:
            pass

    try:
        export_view.Background = list(
            getattr(render_view, "Background", [1.0, 1.0, 1.0]))
        export_view.CameraPosition = captured_camera["CameraPosition"] \
            if captured_camera else list(render_view.CameraPosition)
        export_view.CameraFocalPoint = captured_camera["CameraFocalPoint"] \
            if captured_camera else list(render_view.CameraFocalPoint)
        export_view.CameraViewUp = captured_camera["CameraViewUp"] \
            if captured_camera else list(render_view.CameraViewUp)

        if hasattr(render_view, "CameraParallelScale") \
            and hasattr(export_view, "CameraParallelScale"):
            export_view.CameraParallelScale = render_view.CameraParallelScale
    except Exception:
        pass

    export_displays: List[object] = []
    for r in readers:
        ed = pv.Show(r, export_view)
        try:
            ed.Representation = getattr(args, "representation", None) or "Surface"
        except Exception:
            pass
        export_displays.append(ed)

    active_assoc, active_field = _determine_active_field(args, readers[0])

    for ed in export_displays:
        try:
            if active_field:
                pv.ColorBy(ed, (active_assoc, active_field))
            else:
                pv.ColorBy(ed, None)
        except Exception:
            pass

    lut = None
    if active_field:
        try:
            lut = pv.GetColorTransferFunction(active_field)
            sb = pv.GetScalarBar(lut, export_view)
            sb.Title = active_field
            sb.ComponentTitle = ""
            if hasattr(sb, "RangeLabelFormat"):
                sb.RangeLabelFormat = "%.6g"
            try:
                export_displays[0].SetScalarBarVisibility(export_view, True)
            except Exception:
                try:
                    pv.ShowScalarBarIfNotVisible(lut, export_view)
                except Exception:
                    pass
        except Exception:
            pass

    fixed_range = False
    if active_field and cmin is not None and cmax is not None and cmin < cmax:
        fixed_range = True
        try:
            lut = lut or pv.GetColorTransferFunction(active_field)
            lut.RescaleTransferFunction(float(cmin), float(cmax))
        except Exception:
            pass
        try:
            pwf = pv.GetOpacityTransferFunction(active_field)
            pwf.RescaleTransferFunction(float(cmin), float(cmax))
        except Exception:
            pass
        for obj in (locals().get("lut"), locals().get("pwf")):
            try:
                if obj and hasattr(obj, "AutomaticRescaleRangeMode"):
                    obj.AutomaticRescaleRangeMode = "Never"
            except Exception:
                pass
        print(f"[COLORMAP] Fixed range set to [{cmin}, {cmax}]")

    scene = pv.GetAnimationScene()
    try:
        scene.UpdateAnimationUsingDataTimeSteps()
    except Exception:
        pass
    try:
        tvalues = list(scene.TimeKeeper.TimestepValues)
    except Exception:
        tvalues = []
    if not tvalues:
        tvalues = [None]

    overall_min, overall_max = float("inf"), float("-inf")

    for t in tvalues:
        for r in readers:
            try:
                if t is not None:
                    scene.TimeKeeper.Time = float(t)
                pv.UpdatePipeline(time=t, proxy=r)
            except Exception:
                pass

        if active_field:
            for r in readers:
                try:
                    data = pv.servermanager.Fetch(r)
                    if data is not None:
                        if active_assoc == "POINTS":
                            arr = data.GetPointData().GetArray(active_field)
                        else:
                            arr = data.GetCellData().GetArray(active_field)
                        if arr:
                            rge = arr.GetRange()
                            if rge and len(rge) >= 2:
                                overall_min = min(overall_min, float(rge[0]))
                                overall_max = max(overall_max, float(rge[1]))
                except Exception:
                    pass

            if not fixed_range:
                for ed in export_displays:
                    try:
                        ed.RescaleTransferFunctionToDataRange(True, False)
                    except TypeError:
                        try:
                            pv.GetColorTransferFunction(
                                active_field).RescaleTransferFunctionToDataRange(True)
                            pv.GetOpacityTransferFunction(
                                active_field).RescaleTransferFunctionToDataRange(True)
                        except Exception:
                            pass
                    except Exception:
                        pass

        pv.Render(export_view)

    movie_path = f"{out_base}.{movie_ext}"
    try:
        pv.SaveAnimation(movie_path, export_view,
                         ImageResolution=res, FrameRate=args.fps)
        print(f"[MOVIE] saved: {movie_path} @ {args.fps} fps")
        print(
            f"[RANGE] observed overall data range: [{overall_min}, {overall_max}]")
    except Exception as exc:
        print(f"[MOVIE] SaveAnimation failed: {exc}")
