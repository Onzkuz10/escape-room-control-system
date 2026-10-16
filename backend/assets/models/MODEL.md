# MNIST-12 pretrained handwritten digit CNN

- Source and preprocessing: https://github.com/onnx/models/tree/main/validated/vision/classification/mnist
- Binary: https://media.githubusercontent.com/media/onnx/models/main/validated/vision/classification/mnist/model/mnist-12.onnx
- SHA-256: `5c688690f8bacf667d4c2074af5ad0646ca328d7ab03eccf944a65b320171bdd`
- Size: 26,143 bytes. Model opset: 12. Input: float32 `1×1×28×28`, white strokes on black, values 0–1. Output: ten logits, converted with softmax.
- The upstream model card declares MIT licensing and identifies Microsoft CNTK as its training source. `MODEL-LICENSE.txt` preserves the CNTK MIT notice; `LICENSE.txt` preserves the ONNX Models repository's Apache-2.0 license.

Inference uses the existing OpenCV DNN runtime on CPU. One network instance per thread avoids concurrent mutations. Loading from bytes supports Unicode Windows paths. The model is bundled, verified by checksum, and never downloaded during normal startup.

This is a classifier for individual digits, not a general scene detector or an arbitrary-handwriting recognizer. Empty/multiple glyphs, clipping, crossing-line distractors and near-tied predictions are handled by preprocessing and acceptance rules. Model scores are not calibrated camera accuracy. The legacy `ocr_*` response fields now carry model results for API compatibility.

Run `scripts/check_handwriting.py --download` with the project Python to measure the full preprocessing pipeline against the first 1,000 held-out MNIST samples (also tests dimmed, rotated copies). Reports are written under `runtime/handwriting-test/`. Downloaded handwriting data and derived sample images stay in the ignored runtime folder.
