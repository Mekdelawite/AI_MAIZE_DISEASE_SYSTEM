from validator import ImageValidator

try:

    image = input("Enter image path: ")

    result = ImageValidator.validate(image)

    print()

    print("Image validation successful.")

    print(result)

except Exception as error:

    print()

    print(type(error).__name__)

    print(error)