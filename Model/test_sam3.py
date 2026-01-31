#!/usr/bin/env python3.11
"""
Simple test script to verify SAM3 installation
Tests that all dependencies are installed and SAM3 model can be loaded
"""

import sys

def test_imports():
    """Test that all required packages can be imported"""
    print("=" * 60)
    print("Testing Package Imports...")
    print("=" * 60)

    packages = [
        ("torch", "PyTorch"),
        ("torchvision", "TorchVision"),
        ("transformers", "Transformers"),
        ("huggingface_hub", "HuggingFace Hub"),
        ("cv2", "OpenCV"),
        ("PIL", "Pillow"),
        ("pandas", "Pandas"),
        ("tqdm", "TQDM"),
    ]

    all_passed = True
    for module, name in packages:
        try:
            __import__(module)
            print(f"✓ {name:20s} - OK")
        except ImportError as e:
            print(f"✗ {name:20s} - FAILED: {e}")
            all_passed = False

    return all_passed


def test_pytorch():
    """Test PyTorch and check for GPU"""
    print("\n" + "=" * 60)
    print("Testing PyTorch...")
    print("=" * 60)

    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")

        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"GPU device: {torch.cuda.get_device_name(0)}")
            device = "cuda"
        else:
            print("Running on CPU (slower, but works)")
            device = "cpu"

        # Test tensor creation
        test_tensor = torch.randn(3, 224, 224).to(device)
        print(f"✓ Created test tensor on {device}")
        return True, device
    except Exception as e:
        print(f"✗ PyTorch test failed: {e}")
        return False, "cpu"


def test_transformers():
    """Test transformers library"""
    print("\n" + "=" * 60)
    print("Testing Transformers...")
    print("=" * 60)

    try:
        from transformers import AutoModel
        import transformers
        print(f"Transformers version: {transformers.__version__}")

        # Check if version is sufficient
        version_parts = transformers.__version__.split('.')
        major_minor = float(f"{version_parts[0]}.{version_parts[1]}")

        if major_minor >= 4.47:
            print(f"✓ Transformers version {transformers.__version__} supports SAM3")
            return True
        else:
            print(f"⚠ Transformers version {transformers.__version__} may not support SAM3")
            print("  Recommended: 4.47.0+")
            return False
    except Exception as e:
        print(f"✗ Transformers test failed: {e}")
        return False


def test_huggingface_auth():
    """Test HuggingFace authentication"""
    print("\n" + "=" * 60)
    print("Testing HuggingFace Authentication...")
    print("=" * 60)

    import os
    from pathlib import Path

    # Check for token file
    token_path = Path.home() / ".huggingface" / "token"

    if token_path.exists():
        print("✓ HuggingFace token found")
        print(f"  Location: {token_path}")
        return True
    else:
        print("✗ HuggingFace token NOT found")
        print("\nTo authenticate:")
        print("1. Get your token from: https://huggingface.co/settings/tokens")
        print("2. Run: python3.11 -c \"from huggingface_hub import login; login()\"")
        print("3. Or set HF_TOKEN environment variable")
        return False


def test_sam3_model_access():
    """Test if SAM3 model can be accessed"""
    print("\n" + "=" * 60)
    print("Testing SAM3 Model Access...")
    print("=" * 60)

    try:
        from huggingface_hub import model_info

        model_id = "facebook/sam3-large"
        print(f"Checking access to: {model_id}")

        try:
            info = model_info(model_id)
            print(f"✓ Model accessible: {model_id}")
            print(f"  Model card found")
            return True
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg:
                print(f"✗ Access denied to {model_id}")
                print("\nTo get access:")
                print("1. Visit: https://huggingface.co/facebook/sam3-large")
                print("2. Click 'Request Access' button")
                print("3. Wait for approval (usually hours to days)")
                print("4. Make sure you're logged in (see above)")
            elif "404" in error_msg:
                print(f"⚠ Model not found: {model_id}")
                print("  Note: SAM3 may not be released yet or model ID changed")
            else:
                print(f"✗ Error accessing model: {e}")
            return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_sam3_model_load():
    """Test loading SAM3 model (requires auth)"""
    print("\n" + "=" * 60)
    print("Testing SAM3 Model Loading...")
    print("=" * 60)

    try:
        from sam3_model import SAM3Model

        print("Attempting to load SAM3 model...")
        print("(This may take a few minutes on first run to download ~3GB)")

        model = SAM3Model(
            model_id="facebook/sam3-large",
            device="cpu"  # Use CPU for testing
        )

        success = model.load_model()

        if success:
            print("✓ SAM3 model loaded successfully!")
            return True
        else:
            print("✗ Failed to load SAM3 model")
            return False

    except Exception as e:
        print(f"✗ SAM3 model load failed: {e}")
        print("\nThis is expected if:")
        print("- You haven't requested access to SAM3 on HuggingFace")
        print("- You haven't authenticated with HuggingFace")
        print("- SAM3 model is not yet available")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("SAM3 INSTALLATION TEST")
    print("=" * 60)
    print()

    results = []

    # Test 1: Imports
    results.append(("Package Imports", test_imports()))

    # Test 2: PyTorch
    pytorch_ok, device = test_pytorch()
    results.append(("PyTorch", pytorch_ok))

    # Test 3: Transformers
    results.append(("Transformers", test_transformers()))

    # Test 4: HuggingFace Auth
    auth_ok = test_huggingface_auth()
    results.append(("HuggingFace Auth", auth_ok))

    # Test 5: SAM3 Model Access (only if authenticated)
    if auth_ok:
        results.append(("SAM3 Model Access", test_sam3_model_access()))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8s} {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("\nYou're ready to use SAM3 for pothole detection!")
        print("\nNext steps:")
        print("1. Process a video: python3.11 main.py your_video.mp4")
        print("2. Or test with webcam: python3.11 main.py 0 --live")
    else:
        print("⚠ SOME TESTS FAILED")
        print("\nFollow the instructions above to fix failed tests.")
        print("Most common issues:")
        print("1. Need to authenticate: python3.11 -c \"from huggingface_hub import login; login()\"")
        print("2. Need to request SAM3 access: https://huggingface.co/facebook/sam3-large")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
