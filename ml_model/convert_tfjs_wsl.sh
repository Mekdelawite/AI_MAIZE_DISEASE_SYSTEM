#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/mnt/d/Projects/AI_MAIZE_DISEASE_SYSTEM"
CONVERTER_PYTHON="/home/nigus/.venv-tfjs-convert/bin/python"
CONVERTER="/home/nigus/.venv-tfjs-convert/bin/tensorflowjs_converter"
SOURCE_MODEL="$PROJECT_ROOT/ml_model/models/best_model.h5"
OUTPUT_DIR="$PROJECT_ROOT/frontend/public/models/maize"

if [[ ! -x "$CONVERTER" ]]; then
  echo "TensorFlow.js converter is missing from $CONVERTER" >&2
  exit 1
fi
if [[ ! -f "$SOURCE_MODEL" ]]; then
  echo "Source model is missing: $SOURCE_MODEL" >&2
  exit 1
fi
if [[ -e "$OUTPUT_DIR" ]]; then
  echo "Refusing to overwrite existing output: $OUTPUT_DIR" >&2
  exit 1
fi

before_hash="$(sha256sum "$SOURCE_MODEL" | cut -d ' ' -f 1)"
"$CONVERTER" --input_format=keras "$SOURCE_MODEL" "$OUTPUT_DIR"
"$CONVERTER_PYTHON" "$PROJECT_ROOT/ml_model/normalize_tfjs_model.py" "$OUTPUT_DIR/model.json"

"$CONVERTER_PYTHON" - "$OUTPUT_DIR" <<'PY'
import json
from pathlib import Path
import sys

output = Path(sys.argv[1])
model_json = output / "model.json"
if not model_json.is_file() or model_json.stat().st_size == 0:
    raise SystemExit("model.json was not generated")
artifacts = json.loads(model_json.read_text(encoding="utf-8"))
if artifacts.get("format") != "layers-model":
    raise SystemExit("Unexpected model format")
shards = [output / path for group in artifacts.get("weightsManifest", []) for path in group["paths"]]
if not shards or any(not shard.is_file() or shard.stat().st_size == 0 for shard in shards):
    raise SystemExit("A required model weight shard is missing or empty")
for path in [model_json, *shards]:
    print(f"{path.name}\t{path.stat().st_size} bytes")
PY

after_hash="$(sha256sum "$SOURCE_MODEL" | cut -d ' ' -f 1)"
if [[ "$before_hash" != "$after_hash" ]]; then
  echo "Source model hash changed during conversion" >&2
  exit 1
fi
echo "Original model SHA-256 unchanged: $after_hash"
