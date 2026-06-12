from exceptions import *

try:
    raise ImageNotFoundError("Image does not exist.")

except InferenceError as error:
    print("Caught:", error)