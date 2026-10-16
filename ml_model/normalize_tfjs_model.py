"""Normalize the Keras 3 InputLayer shape key for TF.js Layers readers."""

import json
from pathlib import Path
import sys


def tensor_references(value, result):
    if isinstance(value, dict):
        if value.get("class_name") == "__keras_tensor__":
            history = value.get("config", {}).get("keras_history")
            if history and len(history) >= 3:
                result.append([history[0], history[1], history[2], {}])
            return
        for nested in value.values():
            tensor_references(nested, result)
    elif isinstance(value, list):
        for nested in value:
            tensor_references(nested, result)


model_json = Path(sys.argv[1])
artifacts = json.loads(model_json.read_text(encoding="utf-8"))
model_config = artifacts.get("modelTopology", {}).get("model_config", {}).get("config", {})
for endpoint_key in ("input_layers", "output_layers"):
    endpoints = model_config.get(endpoint_key)
    if isinstance(endpoints, list) and len(endpoints) == 3 and isinstance(endpoints[0], str):
        model_config[endpoint_key] = [endpoints]
layers = model_config.get("layers", [])
layer_types = {layer.get("name"): layer.get("class_name") for layer in layers}
shape_changes = 0
node_changes = 0
dtype_changes = 0
for layer in layers:
    raw_nodes = layer.get("inbound_nodes", [])
    if raw_nodes and isinstance(raw_nodes[0], dict):
        converted_nodes = []
        for node in raw_nodes:
            references = []
            tensor_references(node.get("args", []), references)
            converted_nodes.append(references)
        layer["inbound_nodes"] = converted_nodes
        node_changes += 1
    elif raw_nodes and isinstance(raw_nodes[0], list):
        node_changes += 1

    if layer.get("class_name") == "InputLayer":
        config = layer.setdefault("config", {})
        if "batch_shape" in config and "batchInputShape" not in config:
            config["batchInputShape"] = config.pop("batch_shape")
            shape_changes += 1
        elif "batchInputShape" in config:
            shape_changes += 1

    config = layer.get("config", {})
    dtype = config.get("dtype")
    if isinstance(dtype, dict) and dtype.get("class_name") == "DTypePolicy":
        config["dtype"] = dtype.get("config", {}).get("name", "float32")
        dtype_changes += 1

if shape_changes != 1 or node_changes == 0:
    raise SystemExit(f"Unexpected Keras 3 graph: shape changes={shape_changes}, inbound-node layers={node_changes}")

# Keras 3 calls this variable "kernel" on DepthwiseConv2D. TensorFlow.js
# Layers retains the Keras 2 name "depthwise_kernel".
weight_name_changes = 0
for group in artifacts.get("weightsManifest", []):
    for weight in group.get("weights", []):
        layer_name, separator, variable_name = weight.get("name", "").rpartition("/")
        if separator and layer_types.get(layer_name) == "DepthwiseConv2D" and variable_name == "kernel":
            weight["name"] = f"{layer_name}/depthwise_kernel"
            weight_name_changes += 1

model_json.write_text(json.dumps(artifacts, separators=(",", ":")), encoding="utf-8")
print(f"Normalized InputLayer/endpoints, {node_changes} layer inbound-node entries, {dtype_changes} dtype policies, and {weight_name_changes} DepthwiseConv2D weight names; weight data was not changed")
