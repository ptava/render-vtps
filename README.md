
# render-vtps

A `pvpython` script to render time-series **VTP** files (e.g., from OpenFOAM post-processing) with **ParaView** and export an animation with fixed or per-frame color scaling.

---

## Requirements

- **ParaView** with `pvpython` available on your system `PATH`.  
  Typical check:
  ```bash
  pvpython --version
  ```
- A directory tree with **time directories** (e.g., `0`, `0.1`, `1`, …) containing **.vtp** files.

> Note: Supported movie formats depend on your ParaView build (OSMesa/headless vs. desktop).

---

## Quick Start

From inside the project folder:

```bash
pvpython scripts/render_vtps.py   --time_dirs_path path/to/case/postProcessing/surfaces   --range 0,1   --output_folder ./out
```

This will:
1) Discover time directories in `--time_dirs_path`,  
2) Pick the VTP filename (or a specific one if you pass `--vtp_filename`),  
3) Render a movie named `animation.avi` by default in `--output_folder`.

---

## Command-Line Interface

```
pvpython scripts/render_vtps.py
```

**Options**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--vtp_filename` | str | *(first found)* | Specific VTP filename to load from each time directory. |
| `--time_dirs_path` | str | `.` | Path that contains time directories (`0`, `0.1`, `1`, …). |
| `--stl_file` | str | — | Optional STL geometry to include in the render. |
| `--background_color` | str | `white` | Background color: `white` or `black`. |
| `--field` | str | *(auto)* | Data array to color by. Falls back to the first available (POINTS or CELLS). |
| `--range` | str | — | Fixed colormap range: `min,max` or `min:max` (example: `0,1`). |
| `--output_folder` | str | `.` | Destination folder for the exported movie. |
| `--animation_filename` | str | `animation` | Basename of the output movie (without extension). |
| `--output_format` | str | `avi` | Movie format/extension (e.g., `avi`, `mp4`, depending on your build). |
| `--representation` | str | `Surface` | ParaView representation (e.g., `Surface`, `Surface With Edges`, `Wireframe`, `Volume`). |
| `--render_size` | str | `1280x720` | Output resolution (e.g., `1920x1080`). |
| `--camera_view_point` | str | — | 9 numbers: `[pos_x,pos_y,pos_z,focal_x,focal_y,focal_z,up_x,up_y,up_z]`. |
| `--interactive_mode` | flag | `False` | Open a window to adjust camera and optionally choose field. |
| `--fps` | int | `30` | Frames per second for the output movie. |

---

## Typical Workflows

### 1) Fixed Range for Consistent Coloring
Use a **fixed** color scale to avoid per-frame rescaling (great for comparisons over time):
```bash
pvpython scripts/render_vtps.py   --time_dirs_path ./surfaces   --vtp_filename p_field.vtp   --field p   --range -50,150   --output_folder ./out   --animation_filename p_movie   --output_format avi   --render_size 1920x1080   --fps 24
```

### 2) Let It Auto-Rescale Per Frame
If you **omit** `--range`, the tool will still require it (by design). If you want per‑frame rescaling, provide a wide range that comfortably covers your values (e.g., `--range 0,1` for normalized fields) and the per-frame appearance will still be stabilized by the fixed range. For strictly automatic per-frame scaling, adapt the code in `animation.py` (see the `fixed_range` logic).

### 3) Interactive Camera + Reusable Camera String
```bash
pvpython scripts/render_vtps.py   --time_dirs_path ./surfaces   --range 0,1   --interactive_mode
```
- A window opens; set your camera and close the window.  
- The script prints a **reusable camera string**, e.g.:
  ```
  --camera_view_point '[1.2,0.5,0.3,  0,0,0,  0,1,0]'
  ```
- Next runs can be scripted with that exact camera.

---

## Notes on Fields and Arrays

- The tool lists and picks between **POINTS** and **CELLS** arrays.  
- If you pass `--field` and it isn't found, it falls back to the first available array and warns you.
- On **Volume** rendering or special representations, make sure your chosen field is appropriate.

---

## Output & Formats

- Output movie path: `--output_folder/--animation_filename.--output_format`  
  Example: `./out/animation.avi`
- Supported formats depend on the ParaView build/FFmpeg availability. If `mp4` fails, try `avi` or `ogv`.

---

## Headless / HPC Tips

- Prefer a ParaView build with **OSMesa** for offscreen rendering.  
- If you’re on a remote node without X, ensure your environment is configured for offscreen OpenGL.
- If you see OpenGL/GLX errors, try an interactive node with X forwarding or switch to an OSMesa-enabled build.

---

## Project Layout

```
render_vtps_refactor/
├── render_vtps/
│   ├── __init__.py         # Package metadata
│   ├── animation.py        # Movie generation (SaveAnimation + colorbar)
│   ├── cli.py              # Argparse + top-level orchestration
│   ├── discovery.py        # Find time dirs and VTP files
│   ├── interactive.py      # Interactive camera + field selection
│   ├── pv_helpers.py       # ParaView helpers (coloring, arrays, session)
│   └── utils.py            # Parsing helpers (ranges, sizes, camera vectors)
└── scripts/
    └── render_vtps.py      # pvpython entry point
```

---

## Troubleshooting

- **No VTP files found**: Check `--time_dirs_path` and that time directories contain `.vtp` files.  
- **Field not found**: Use `--interactive_mode` to list arrays and copy the correct name, or omit `--field` to auto-pick.  
- **Movie save fails**: Try a different `--output_format`. Ensure your ParaView has FFmpeg support.  
- **Black/white frames**: Verify `--representation` and background; ensure your OpenGL/offscreen setup is valid.

---

## Acknowledgements

Built on ParaView (`paraview.simple`) and designed for OpenFOAM-style time-series post‑processing.

---

## Install

### Option A — From the project directory
```bash
pip install -e .
```
This installs a console command called `render-vtps` that will call ParaView’s `pvpython` under the hood.

### Option B — From Git
```bash
pip install git+https://github.com/ptava/render-vtps.git
```
> Note: ParaView itself is **not** installed via pip. This package expects `pvpython` to already exist on your system.

---

## Selecting the `pvpython` binary

By default, the launcher tries `pvpython` on your `PATH`.  
To specify a custom one (e.g., from a ParaView install):

**Linux/macOS**
```bash
export PVPYTHON=/path/to/ParaView/bin/pvpython
render-vtps --help
```

---

## Usage
User can run `render-vtps` from the command line after installation or use the following:
```bash
pvpython -m render_vtps.cli --time_dirs_path <path> --range 0,1 --output_folder ./out
```
or
```bash
pvpython scripts/render_vtps.py --time_dirs_path <path> --range 0,1 --output_folder ./out
```
`render-vtps.py` is a wrapper whose only job is to call `render_vtps.cli:main`

---

## Uninstall
```bash
pip uninstall render-vtps
```
