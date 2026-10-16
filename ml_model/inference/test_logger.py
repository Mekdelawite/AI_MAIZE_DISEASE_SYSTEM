from logger import *

log_prediction(

    image_name="Corn_Blight (1134).jpg",

    disease="Blight",

    confidence=96.52,

    prediction_time=0.118

)

log_error(

    image_name="test.jpg",

    error="ImageNotFoundError"

)

print("Logs written successfully.")