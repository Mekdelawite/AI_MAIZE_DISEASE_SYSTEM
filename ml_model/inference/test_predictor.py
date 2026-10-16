import json

from predictor import DiseasePredictor

predictor = DiseasePredictor()

while True:

    print()

    image = input(
        "Image path (q to quit): "
    ).strip()

    if image.lower() == "q":
        break

    try:

        result = predictor.predict(image)

        print()

        print(json.dumps(

            result,

            indent=4

        ))

    except Exception as error:

        print()

        print(type(error).__name__)

        print(error)