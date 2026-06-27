from __future__ import annotations

import platform
import shutil
import subprocess


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def has_nvidia_gpu() -> bool:
    if not command_exists("nvidia-smi"):
        return False
    result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, check=False)
    return result.returncode == 0


def main() -> None:
    system = platform.system()
    machine = platform.machine()

    print(f"Platform: {system} {machine}")
    print()
    print("Install local API dependencies first:")
    print("  pip install -r local-transformers-openai-api/requirements.txt")
    print()

    if system == "Darwin":
        print("Detected macOS. Do not install CUDA wheels.")
        print("Install PyTorch with Apple CPU/MPS support:")
        print("  pip install torch")
        return

    if system == "Linux" and has_nvidia_gpu():
        print("Detected Linux with NVIDIA GPU.")
        print("Install the PyTorch CUDA wheel matching your driver/CUDA stack.")
        print("Example for CUDA 12.4:")
        print("  pip install torch --index-url https://download.pytorch.org/whl/cu124")
        return

    if system == "Linux":
        print("Detected Linux without visible NVIDIA GPU.")
        print("Install CPU-only PyTorch to avoid downloading CUDA packages:")
        print("  pip install torch --index-url https://download.pytorch.org/whl/cpu")
        return

    print("Unsupported or uncommon platform.")
    print("Install PyTorch manually using the official selector:")
    print("  https://pytorch.org/get-started/locally/")


if __name__ == "__main__":
    main()
