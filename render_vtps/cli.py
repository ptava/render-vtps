
"""Command-line interface for render_vtps."""
from __future__ import annotations

import argparse
from typing import Dict, List, Tuple

from .animation import generate_animation
from .discovery import find_vtp_files, validate_vtp_file
from .interactive import interactive_camera_setup
from .pv_helpers import apply_coloring, discover_arrays
from .visualize import pv_visualize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a video from VTP time-series data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--vtp",
        "--vtp-filename",
        "--vtp_filename",
        dest="vtp_filename",
        type=str,
        action="append",
        help="VTP filename to load from each time directory. Repeat if you use multiple --path values.",
    )
    parser.add_argument(
        "--path",
        "--time-dirs-path",
        "--time_dirs_path",
        dest="time_dirs_path",
        type=str,
        action="append",
        help="Directory containing time-step folders. Repeat to render multiple sources together.",
    )
    parser.add_argument(
        "--stl",
        "--stl-file",
        "--stl_file",
        dest="stl_file",
        type=str,
        action="append",
        help="Optional STL file to show with the VTP data. Repeat to load multiple geometries.",
    )
    parser.add_argument(
        "--background",
        "--background-color",
        "--background_color",
        dest="background",
        type=str,
        default="1,1,1",
        help="Background RGB as 'r,g,b' with values in 0-1 or 0-255.",
    )
    parser.add_argument(
        "--field",
        type=str,
        help="Field to visualize. Defaults to the first available array.",
    )
    parser.add_argument(
        "--range",
        required=False,
        default=None,
        help="Fixed colormap range as 'min,max' or 'min:max' (e.g., 0,1).",
    )
    parser.add_argument(
        "--time-location",
        "--time_location",
        dest="time_location",
        required=False,
        default="Upper Left Corner",
        help="Location of the time annotation.",
    )
    parser.add_argument(
        "--output",
        "--output-folder",
        "--output_folder",
        dest="output_folder",
        type=str,
        default=".",
        help="Output folder for the rendered animation.",
    )
    parser.add_argument(
        "--name",
        "--animation-filename",
        "--animation_filename",
        dest="animation_filename",
        type=str,
        default="animation",
        help="Output animation basename, without extension.",
    )
    parser.add_argument(
        "--format",
        "--output-format",
        "--output_format",
        dest="output_format",
        type=str,
        default="avi",
        help="Output movie format/extension.",
    )
    parser.add_argument(
        "--representation",
        type=str,
        action="append",
        help=(
            "Representation for each rendered surface. Pass once to use the same "
            "representation everywhere, or repeat once per --path."
        ),
    )
    parser.add_argument(
        "--size",
        "--render-size",
        "--render_size",
        dest="render_size",
        type=str,
        default="1280x720",
        help="Render size as WxH.",
    )
    parser.add_argument(
        "--camera",
        "--camera-view-point",
        "--camera_view_point",
        dest="camera_view_point",
        type=str,
        help=(
            "Camera view point with a sequence of 9 numbers: "
            "[pos_x,pos_y,pos_z,focal_x,focal_y,focal_z,up_x,up_y,up_z]"
        ),
    )
    parser.add_argument(
        "--interactive",
        "--interactive-mode",
        "--interactive_mode",
        dest="interactive_mode",
        action="store_true",
        help="Enable interactive camera setup mode.",
        default=False,
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Frames per second for the output video.",
    )
    parser.add_argument(
        "--collections",
        action="store_true",
        default=False,
        help="Write per-surface ParaView collection folders alongside the video output.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    time_paths: List[str] = args.time_dirs_path or ["."]
    vtp_names: List[str | None] = args.vtp_filename or [None] * len(time_paths)
    if len(vtp_names) == 1 and len(time_paths) > 1:
        vtp_names = vtp_names * len(time_paths)
    if len(vtp_names) != len(time_paths):
        raise ValueError("Number of --vtp_filename must match --time_dirs_path")

    source_representations: List[str] = args.representation or ["Surface"]
    if len(source_representations) == 1 and len(time_paths) > 1:
        source_representations = source_representations * len(time_paths)
    if len(source_representations) != len(time_paths):
        raise ValueError("Number of --representation must match --path")
    args.source_representations = source_representations

    sources: List[Tuple[List[str], str]] = []
    for path, vtp_name in zip(time_paths, vtp_names):
        time_dirs, vtp_files = find_vtp_files(path)
        selected = validate_vtp_file(vtp_name, vtp_files)
        sources.append((time_dirs, selected))

    readers, render_view, displays = pv_visualize(args, sources)

    captured_camera: Dict | None = None
    if args.interactive_mode and readers:
        camera_position, camera_focal_point, camera_view_up, selected = \
            interactive_camera_setup(readers[0], render_view, displays[0])
        if selected:
            args.field = selected
            pt, cl = discover_arrays(readers[0])
            assoc = "POINTS" if selected in pt else "CELLS"
            for disp in displays:
                apply_coloring(disp, assoc, selected)
        captured_camera = {
            "CameraPosition": camera_position,
            "CameraFocalPoint": camera_focal_point,
            "CameraViewUp": camera_view_up,
        }

    generate_animation(args, readers, render_view, captured_camera)


    if __name__ == "__main__":  # pragma: no cover
        main()
