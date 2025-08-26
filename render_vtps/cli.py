
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
        description="Generate video from OpenFOAM VTP time series files.",
    )

    parser.add_argument(
        "--vtp_filename",
        type=str,
        action="append",
        help="Specify VTP filename (can be repeated)",
    )
    parser.add_argument(
        "--time_dirs_path",
        type=str,
        action="append",
        help="Specify directory where time dirs are stored (can be repeated)",
    )
    parser.add_argument(
        "--background_color",
        type=str,
        default="white",
        help="Set background color (default: white)",
    )
    parser.add_argument(
        "--field",
        type=str,
        help="Specify the field to visualize (default: first available)"
    )
    parser.add_argument(
        "--range",
        required=False,
        default=None,
        help="Fixed colormap range as 'min,max' or 'min:max' (e.g., 0,1).",
    )
    parser.add_argument(
        "--output_folder",
        type=str,
        default=".",
        help="Set output folder (default: '.')"
    )
    parser.add_argument(
        "--animation_filename",
        type=str,
        default="animation",
        help="Set animation file name (default: animation)"
    )
    parser.add_argument(
        "--output_format",
        type=str,
        default="avi",
        help="Animation format/extension (default: avi)"
    )
    parser.add_argument(
        "--representation",
        type=str,
        default="Surface",
        help="Specify representation of mesh (e.g. Surface, Surface With Edges)",
    )
    parser.add_argument(
        "--render_size",
        type=str,
        default="1280x720",
        help="Set render size (e.g. 1280x720)"
    )
    parser.add_argument(
        "--camera_view_point",
        type=str,
        help=(
            "Set camera view point with a sequence of 9 numbers: "
            "[pos_x,pos_y,pos_z,focal_x,focal_y,focal_z,up_x,up_y,up_z]"

        ),
    )
    parser.add_argument(
        "--interactive_mode",
        action="store_true",
        help="Enable interactive camera setup mode",
        default=False
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Frames per second for the output video (default: 30)"
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
