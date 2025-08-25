
"""Command-line interface for render_vtps."""
from __future__ import annotations

import argparse
from typing import Dict

from .animation import generate_animation
from .discovery import find_vtp_files, validate_vtp_file
from .interactive import interactive_camera_setup
from .visualize import pv_visualize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate video from OpenFOAM VTP time series files.",
    )

    parser.add_argument(
        "--vtp_filename",
        type=str,
        help="Specify VTP filename (default: first one found)"
    )
    parser.add_argument(
        "--time_dirs_path",
        type=str,
        default=".",
        help="Specify directory where time dirs are stored (default: current dir)",
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

    time_dirs, vtp_files = find_vtp_files(args.time_dirs_path)
    selected_vtp_filename = validate_vtp_file(args.vtp_filename, vtp_files)

    reader, render_view, display = pv_visualize(
        args, time_dirs, selected_vtp_filename)

    captured_camera : Dict | None = None
    if args.interactive_mode:
        camera_position, camera_focal_point, camera_view_up, selected = \
            interactive_camera_setup(reader, render_view, display)
        if selected:
            args.field = selected
        captured_camera = {
            "CameraPosition": camera_position,
            "CameraFocalPoint": camera_focal_point,
            "CameraViewUp": camera_view_up,
        }

    generate_animation(args, reader, render_view, captured_camera)


    if __name__ == "__main__":  # pragma: no cover
        main()
