#!/usr/bin/env python3
"""
Download and cache the SAM3 model from Hugging Face (no full pipeline).
Run this once so the model is ready when you run main.py or the live stream.
Usage: python3.11 download_model.py
       or: python3.11 -m Model.download_model  (from repo root)
"""

import sys


def main():
    model_id = "facebook/sam3"
    print(f"Downloading SAM3 model: {model_id}")
    print("This may take a while (~3.4 GB). Progress will be shown below.\n")

    try:
        from transformers import Sam3Model, Sam3Processor
    except ImportError:
        print("Error: transformers not installed. Run: pip install -r requirements.txt")
        sys.exit(1)

    try:
        print("Downloading processor...")
        Sam3Processor.from_pretrained(model_id)
        print("Processor cached.\n")

        print("Downloading model (this is the large file)...")
        Sam3Model.from_pretrained(model_id)
        print("Model cached.\n")

        print("Done. Model is cached at:")
        print("  ~/.cache/huggingface/hub/")
        print("\nYou can now run Kavi without waiting for the download.")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you:")
        print("  1. Have access to facebook/sam3: https://huggingface.co/facebook/sam3")
        print("  2. Are logged in: export HF_TOKEN='hf_...' or run huggingface_hub login")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
