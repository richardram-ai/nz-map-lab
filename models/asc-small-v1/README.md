# Aotearoa Species Classifier (small model)

Used by the phone form to suggest species from a photo. The suggestions run on the phone; photos are not sent anywhere for identification.

- Made by the TAIAO project at the University of Waikato and the University of Canterbury: https://github.com/Waikato/aotearoa-species-classifier
- Source file: species_classifier_fp32_384_384.onnx from release model-small-onnx-fp32-384-v1.0
  (SHA-256 1905b995f53f58cfab8c611c388ff670bab2dcb5019e8cceec0937e9f0291e68)
- Licence: model weights CC BY-NC 4.0 (https://creativecommons.org/licenses/by-nc/4.0/). Initialised from
  timm/tf_efficientnetv2_s.in21k, Apache-2.0 (https://huggingface.co/timm/tf_efficientnetv2_s.in21k).
- Non-commercial use only.

## Changes made here

- Weights are stored at half precision (float16) and converted back to full precision when the model loads,
  so calculations run at full precision. This halves the download (157 MB to 79 MB). On 48 test photos the
  top suggestion matched the original every time, and confidence scores were within 0.4 percentage points.
- The file is split into four parts (model.part0 to model.part3) because the host limits single files to 25 MB.
  Join them in order to get the ONNX file back.
- labels.json is a slimmed copy of species_14991_metadata.json from the same repository:
  [scientific name, common name, Māori name, MPI flags (n = notifiable, u = unwanted), kingdom initial].
