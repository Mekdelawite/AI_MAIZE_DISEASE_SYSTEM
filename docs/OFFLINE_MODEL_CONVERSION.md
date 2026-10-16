# Offline browser model

## Converted model

The source file `ml_model/models/best_model.h5` is read-only during conversion. The TensorFlow.js Layers model is stored in `frontend/public/models/maize/`.

The conversion was run in Ubuntu WSL 2 with the separate Python 3.11.17 environment at `/home/nigus/.venv-tfjs-convert`. Its verified packages are TensorFlow 2.19.0, Keras 3.10.0, TensorFlow.js converter 4.22.0, TensorFlow Decision Forests 1.12.0, YDF 0.15.0, and setuptools 81.0.0. `uv pip check` reported no incompatible requirements. YDF 0.15.0 avoids the Protobuf generated-code mismatch observed with YDF 0.16.0. Setuptools 81.0.0 retains `pkg_resources`, which TensorFlow Hub 0.16.1 still imports.

From Ubuntu WSL, the guarded conversion script is:

```bash
bash /mnt/d/Projects/AI_MAIZE_DISEASE_SYSTEM/ml_model/convert_tfjs_wsl.sh
```

It refuses to overwrite an existing output directory, verifies every weight shard, prints file sizes, and checks that the original H5 SHA-256 is unchanged.

The converter command used was:

```bash
/home/nigus/.venv-tfjs-convert/bin/tensorflowjs_converter \
  --input_format=keras \
  /mnt/d/Projects/AI_MAIZE_DISEASE_SYSTEM/ml_model/models/best_model.h5 \
  /mnt/d/Projects/AI_MAIZE_DISEASE_SYSTEM/frontend/public/models/maize
```

The TensorFlow.js 4.22 reader uses Keras 2 style functional graph metadata while the H5 model stores Keras 3 metadata. The conversion script adapts the InputLayer shape, functional input/output references, inbound-node connections, dtype policy values, and DepthwiseConv2D weight names for the TF.js reader. It does not alter weight values or add preprocessing to the model.

Generated files in `frontend/public/models/maize/`:

| File | Size |
| --- | ---: |
| `model.json` | 114,782 bytes |
| `group1-shard1of3.bin` | 4,194,304 bytes |
| `group1-shard2of3.bin` | 4,194,304 bytes |
| `group1-shard3of3.bin` | 663,824 bytes |

The source file SHA-256 before and after conversion was `23A039422885948F6B2C272782196FC3876FB5D4C982255A5071E6023B8548D3`.

## Prediction parity

Run the labeled test-image comparison from Ubuntu WSL after installing the frontend dependencies:

```bash
/home/nigus/.venv-maize-test/bin/python \
  /mnt/d/Projects/AI_MAIZE_DISEASE_SYSTEM/ml_model/verify_tfjs_conversion.py \
  --samples-per-class 3
```

This uses the same RGB conversion, 224×224 resize, and MobileNetV2 preprocessing for the source Keras model and the TensorFlow.js model. The 12-image comparison (3 per class) matched the predicted class on all 12 samples. Mean absolute probability difference was `1.9232e-7`; the maximum was `1.2368e-6`. Two images were misclassified by both model formats, so class agreement here verifies conversion parity, not model accuracy. Per-image predictions are in `ml_model/reports/tfjs_prediction_parity.json`.

## Browser behavior

The local diagnosis action runs TensorFlow.js in the browser and does not call Flask. The service worker caches same-origin application assets and each successful model JSON/weight request. API paths are excluded from caching. A local prediction does not create a server diagnosis/history record and has no server-generated advisory or Grad-CAM heatmap. The existing online diagnosis and offline synchronization queue remain separate.

Production browser smoke test (Microsoft Edge headless) passed against the built app at `http://127.0.0.1:4173`: it loaded the app and model online, ran local inference, switched the browser offline, reloaded the diagnosis route, selected the same labeled image, and ran local inference again (`Healthy`). The service worker controlled the page and CacheStorage contained `model.json` and all three weight shards. No `/api/diagnosis/complete` request was made. This checks the local inference path and model cache; authenticated online endpoints were not tested by this smoke test.

To repeat the check manually, run `cd frontend`, `npm run build`, then `npm run preview -- --host 127.0.0.1 --port 4173`. Open that local URL, visit the diagnosis page, and run **Diagnose on this device** once online so the model and app assets finish downloading. Use DevTools Network → **Offline**, reload, choose an image, and run **Diagnose on this device** again. Online diagnosis, server advisory/Grad-CAM, and server history synchronization require connectivity. Local predictions do not create a server diagnosis record. The browser can fall back to CPU inference when WebGL is unavailable; inference worked in the Edge test, though CPU performance depends on the device.
