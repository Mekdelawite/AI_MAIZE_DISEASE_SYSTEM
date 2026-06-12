import os
from predictor import DiseasePredictor

predictor = DiseasePredictor()

image_path = input("Enter image path: ").strip()

if not os.path.exists(image_path):
    print("\n❌ Error: Image not found!")
    print(f"Path: {os.path.abspath(image_path)}")
else:
    result = predictor.predict(image_path)

    print("\nPrediction Result")
    print("-" * 30)

    for key, value in result.items():
        print(f"{key}: {value}")