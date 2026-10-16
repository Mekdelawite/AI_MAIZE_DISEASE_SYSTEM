import numpy as np

from utils import *

prediction = np.array([[

    0.02,

    0.95,

    0.02,

    0.01

]])

print()

print("Best Prediction")

print("-" * 40)

print(get_best_prediction(prediction))

print()

print("Top Predictions")

print("-" * 40)

for item in get_top_predictions(prediction):

    print(item)