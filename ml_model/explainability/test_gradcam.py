"""
Basic Grad-CAM engine test.
"""

from gradcam import GradCAM


def main():

    print()
    print("=" * 60)
    print("GRAD-CAM ENGINE TEST")
    print("=" * 60)
    print()

    gradcam = GradCAM()

    print()
    print("Target layer:")
    print(gradcam.target_layer.name)

    print()

    print("Target layer output:")
    print(gradcam.target_layer.output.shape)

    print()

    print("Grad-CAM engine initialized successfully.")


if __name__ == "__main__":
    main()