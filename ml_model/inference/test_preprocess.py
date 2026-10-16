from preprocess import ImagePreprocessor

image_path = input("Enter image path: ")

tensor = ImagePreprocessor.preprocess(image_path)

print()

print("Preprocessing completed successfully.")

print()

print("Tensor Shape :", tensor.shape)

print("Data Type    :", tensor.dtype)

print("Minimum      :", tensor.min())

print("Maximum      :", tensor.max())