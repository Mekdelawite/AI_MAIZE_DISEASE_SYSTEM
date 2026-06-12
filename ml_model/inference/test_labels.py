from labels import *

print()

print("Available Classes")

print("-" * 40)

for disease in DISEASES:

    print(disease)

print()

print(get_disease_by_id(1))

print()

print(get_disease_by_name("Healthy"))