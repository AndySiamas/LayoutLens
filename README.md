# LayoutLens

LayoutLens is an agentic pipeline that turns a natural-language prompt into a simple 3D layout visualization (via an Unreal placeholder importer).

---

## Prerequisites

- Conda (recommended) + Python 3.11
- A local or remote LLM backend:
  - Local (recommended): LM Studio / Ollama / vLLM running an OpenAI-compatible endpoint
  - Remote: OpenAI / Google / Anthropic (requires API key)
- Unreal Engine 5.7 (for the visualizer)

---

## Install

1) Clone

    ```
    git clone https://github.com/AndySiamas/LayoutLens.git
    cd LayoutLens
    ```

2) Create the conda environment

    ```
    conda env create -f environment.yml
    conda activate layout_lens
    ```

3) Install the project

    ```
    pip install -e .[dev]
    ```

---

## Configuration

### `.env` auto-create behavior

On first run, LayoutLens automatically copies `.env.example` → `.env` if `.env` does not exist.

### Edit your `.env`

Common local configuration (LM Studio example):

    # CORE
    LLM_PROVIDER=local
    LLM_BASE_URL=http://localhost:1234/v1
    LLM_MODEL=google/gemma-3-27b
    LLM_API_KEY=
    ROOM_GRID_SIZE=0.25

    # PATHS
    OUTPUT_DIR_PATH=./output

Remote examples:

OpenAI

    LLM_PROVIDER=openai
    LLM_BASE_URL=https://api.openai.com/v1
    LLM_MODEL=gpt-4.1
    LLM_API_KEY=YOUR_KEY_HERE

Google (Gemini)

    LLM_PROVIDER=google
    LLM_MODEL=gemini-1.5-pro
    LLM_API_KEY=YOUR_KEY_HERE

Anthropic (Claude)

    LLM_PROVIDER=anthropic
    LLM_MODEL=claude-3-5-sonnet-latest
    LLM_API_KEY=YOUR_KEY_HERE

---

## Run the pipeline

Recommended (interactive):

    layout-lens

Non-interactive (one command):

    layout-lens --prompt "A large modern bedroom in a rectangular room. Put the bed centered on the back wall with a small nightstand. On the other side of the room, add a desk near a window with a chair. Keep clear walking space from the door to the bed and around the desk, and don’t overcrowd the room."

Alternative: run as a module:

    python -m layout_lens

After running, check `./output/` for the latest run folder and open `room_plan.json`.

---

## Output

Each run creates a unique folder under `./output/<RUN_ID>/`:

- `design.json` — design intent + element list
- `space.json` — room boundary + height + openings (doors/windows)
- `room_plan.json` — placed elements (position, yaw, footprint, height)
- `validation_error.txt` — written when validation/retries fail

Example output folder:

    output/
      20260219_185001_ab12/
        design.json
        space.json
        room_plan.json
        validation_error.txt

---

## Unreal visualizer (UE 5.7)

LayoutLens includes an Unreal C++ plugin that loads `room_plan.json` and spawns placeholder boxes for items that are placed on the floor.


1) Create (or open) an Unreal **C++** project in UE 5.7.

2) Copy the plugin folder into your project:

        YourUnrealProject/Plugins/LayoutLensImporter

3) Generate project files and build:
- Right-click your `.uproject` → **Generate Visual Studio project files**
- Open the `.sln` → Build `Development Editor` (Win64)

4) Open Unreal Editor and enable the plugin:
- **Edit → Plugins** → enable `LayoutLensImporter` (restart if prompted)

5) Add the visualizer actor to your level:
- Create and place a `LayoutLensVisualizerActor` into the scene
- Set `RoomPlanFilePath` to the full path of your generated `room_plan.json`
  (example: `C:\...\layout_lens\output\<RUN_ID>\room_plan.json`)

6) Press Play:
- The plugin will load automatically if `AutoLoadOnBeginPlay` is true
- Press **R** to reload after generating a new JSON

What you should see:
- Simple room walls based on `space.boundary` and `space.height`
- Door/window debug outlines based on `space.openings`
- Placeholder boxes for floor elements (with labels)

---

## Demo prompt ideas

- “A cozy modern bedroom in a rectangular room. Put the bed on the back wall, a nightstand, and a desk near a window. Keep lots of clear walking space.”
- “A simple home office: one desk, one chair, one bookshelf, and a small storage cabinet. Keep it spacious.”
- “A minimal studio apartment layout with a bed, a small table, and one storage unit. Keep wide walkways.”

---

## Troubleshooting

- Nothing generates:
  - Confirm your LLM backend is running and `LLM_BASE_URL` is correct.
  - If using a remote provider, confirm `LLM_API_KEY` is set.

- Unreal shows nothing:
  - Confirm `RoomPlanFilePath` points to a real `room_plan.json` file.
  - Check Unreal Output Log for `LayoutLens:` errors.
  - Make sure your JSON has at least one element with `"placement": "floor"`.

- Google / Anthropic errors:
  - These providers require a valid API key.
  - For local models, use `LLM_PROVIDER=local` and a local `LLM_BASE_URL`.

- Many retries / overlaps:
  - Try fewer elements in the prompt, or a larger room.

---

## Next steps for this project

- Better room creation: generate the room boundary from a simple text/ASCII sketch (or a tiny “draw on grid” UI).
- Better geometry: add lightweight packing rules (bigger “keep-out” margins, fixed walkways, zone-based placement).
- Real meshes: replace placeholder boxes with real assets through AI mesh generation (via modern text/image-to-3D pipelines such as Hunyuan3D).
- Multi-room support: extend `Space` + `RoomPlan` to support multiple rooms and connecting doors.

---
