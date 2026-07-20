"""Convert one audio file through an RVC model.

This script is intentionally tiny so Fibi's main Python can call a separate
Python 3.10 RVC environment without importing heavy ML packages itself.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--index", required=True)
    parser.add_argument("--pitch", type=int, default=0)
    parser.add_argument("--pitch-method", default="rmvpe")
    args = parser.parse_args()

    # rvc-python/fairseq expects legacy checkpoint loading. Keep this patch
    # inside the isolated converter process instead of changing Fibi's app.
    import torch

    original_torch_load = torch.load

    def legacy_torch_load(*load_args, **load_kwargs):
        load_kwargs.setdefault("weights_only", False)
        return original_torch_load(*load_args, **load_kwargs)

    torch.load = legacy_torch_load

    from rvc_python.infer import RVCInference

    rvc = RVCInference(device="cpu:0")
    rvc.load_model(args.model, version="v2", index_path=args.index)
    rvc.set_params(f0up_key=args.pitch, f0method=args.pitch_method)
    rvc.infer_file(args.input, args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"RVC_CONVERT_ERROR: {error}", file=sys.stderr)
        raise
