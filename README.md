# LayoutLens

LayoutLens is a agentic pipeline that turns a natural-language prompt into a 3d layout visualization:

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
    LLM_MODEL=gpt-4.1-mini
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

    layout-lens --prompt "Design a small neighborhood coffee shop with an ordering counter, pickup area, pastry display, tables and chairs, menu board, storage, and a trash bin."

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

### Goal

Read a RoomPlan JSON file and spawn placeholder cubes for `placement == "floor"` items.

### JSON file path workflow (important)

Because each run uses a unique folder, you have two choices:

Preferred: Make the JSON file path configurable in Unreal (UI text input).
Fallback: Add a stable copy step in Python (e.g., copy to `output/latest/room_plan.json` after each run).

### Minimal Blueprint-only plan (high-level)

1) Create an Actor Blueprint: `BP_RoomPlanVisualizer`

2) Add variables:
   - `RoomPlanFilePath` (String) — absolute or relative file path to `room_plan.json`

3) Add a function: `ReloadLayout`
   - Load file → parse JSON → loop `elements`
   - For each element where `placement == "floor"`:
     - Read `transform.x`, `transform.y`, `yaw_deg`, `footprint.width`, `footprint.depth`, `height`
     - Spawn a cube (StaticMeshActor)
     - Convert meters → centimeters (`meters * 100`)
     - Scale cube by width/depth/height
     - Rotate cube by `yaw_deg` around Z

4) Create a simple UMG widget:
   - Text input (path)
   - “Reload” button (calls `ReloadLayout`)

---

## Demo prompt ideas

- “Design a neighborhood coffee shop with an ordering counter, pickup area, pastry display, tables and chairs, menu board, storage, and a trash bin.”
- “Design the interior of a suburban garden shed.”
- “Design a traditional church interior with altar, pews, lectern, and aisle.”

---

## Troubleshooting

- Nothing generates:
  - Confirm your LLM backend is running and `LLM_BASE_URL` is correct.
  - If using a remote provider, confirm `LLM_API_KEY` is set.

- Google / Anthropic errors:
  - These providers require a valid API key.
  - For local models, use `LLM_PROVIDER=local` and a local `LLM_BASE_URL`.

- Many retries / overlaps:
  - Try fewer elements in the prompt, or a larger room.

---

## License

Hackathon prototype. Use at your own risk.