
"""ParaView helper routines (require pvpython / paraview.simple)."""
from __future__ import annotations
# from contextlib import contextmanager

from typing import List, Tuple

try:
    import paraview.simple as pv
    from paraview.simple import (
        ColorBy,
        GetColorTransferFunction,
        GetOpacityTransferFunction,
        UpdatePipeline,
    )
except Exception as exc:
    raise RuntimeError("This module must be run under pvpython with ParaView available.") from exc


def initialize_session() -> None:
    """Start a fresh pv session to avoid stale state across runs."""
    pv.Disconnect()
    pv.Connect()


def discover_arrays(reader) -> Tuple[List[str], List[str]]:
    """Return (point_arrays, cell_arrays) names using data information."""
    try:
        try:
            UpdatePipeline(proxy=reader)
        except TypeError:
            pv.UpdatePipeline()
    except Exception:
        pv.UpdatePipeline()

    di = reader.GetDataInformation()
    pdi = di.GetPointDataInformation()
    cdi = di.GetCellDataInformation()

    def _names(attr_info) -> List[str]:
        names: List[str] = []
        n = attr_info.GetNumberOfArrays()
        for i in range(n):
            try:
                ai = attr_info.GetArrayInformation(i)
                names.append(ai.GetName())
                continue
            except Exception:
                pass
            try:
                ai = attr_info.GetArray(i)
                names.append(ai.GetName())
                continue
            except Exception:
                pass
        return names

    return _names(pdi), _names(cdi)


def apply_coloring(display, assoc: str, name: str) -> None:
    """Color *display* by (assoc, name) and rescale TFs to data range."""
    ColorBy(display, (assoc, name))
    display.RescaleTransferFunctionToDataRange(True, False)
    GetColorTransferFunction(name).RescaleTransferFunctionToDataRange(True)
    GetOpacityTransferFunction(name).RescaleTransferFunctionToDataRange(True)

# @contextmanager
# def suppress_rendering(view):
#     """Temporarily set `view.SuppressRendering` inside the with-block."""
#     original = view.SuppressRendering
#     try:
#         view.SuppressRendering = True
#     except Exception:
#         raise
#     try:
#         yield view
#     finally:
#         view.SuppressRendering = original
