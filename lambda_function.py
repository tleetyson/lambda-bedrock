# Imported modules that will be used within this lambda

import base64
import pandas as pd
import datetime
import io
import json
import logging
import random
import boto3
from PIL import Image
from botocore.config import Config
from botocore.exceptions import ClientError

# Class for creating an error object
class ImageError(Exception):
    "Error image class for when we can't generate an image"
    def __init__(self, message):
        self.message = message

# Function to generate image, the foundational model that will be used is nova-canvas-v1:0
def generate_image(model_id, body):
    logger.info(
        "Generating image with Amazon Nova Canvas  model", model_id)

    bedrock = boto3.client(
        service_name='bedrock-runtime',
        config=Config(read_timeout=300)
    )

    accept = "application/json"
    content_type = "application/json"

    response = bedrock.invoke_model(
        body=body, modelId=model_id, accept=accept, contentType=content_type
    )
    response_body = json.loads(response.get("body").read())

    base64_image = response_body.get("images")[0]
    base64_bytes = base64_image.encode('ascii')
    image_bytes = base64.b64decode(base64_bytes)

    finish_reason = response_body.get("error")

    if finish_reason is not None:
        raise ImageError(f"Image generation error. Error is {finish_reason}")

    logger.info(
        "Successfully generated image with Amazon Nova Canvas  model %s", model_id)

    return image_bytes


def main():
    """
    Entrypoint for Amazon Nova Canvas  example.
    """
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s: %(message)s")
    model_id = 'amazon.nova-canvas-v1:0'
    bucket = "tleetyson-anime-bucket"
    file_name = "anime-quotes.csv"
    s3 = boto3.client('s3') 
    s3_obj = s3.get_object(Bucket= bucket, 
                           Key= file_name) 
    df = pd.read_csv(obj['Body'], 
                     usecols=["Character", "Quote"])
    max_rows = len(df)
    row_position = random.randint(0, max_rows)
    selected_columns = df.columns
    character_to_use = selected_columns["Character"]
    quote_to_use = selected_columns["Quote"]
    row_data = selected_columns.loc[row_position] 
    prompt = f"Please generate colorful picture of {character_to_use} saying {quote_to_use}"

    body = json.dumps({
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": prompt
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "height": 1024,
            "width": 1024,
            "cfgScale": 8.0,
            "seed": 0
        }
    })

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        image_bytes = generate_image(model_id=model_id,
                                     body=body)
        image = Image.open(io.BytesIO(image_bytes))
        image.show()
        s3.put_object(
            Bucket= bucket,
            Key= f"{character_to_use}_quote_{timestamp}.jpg",  # You can generate dynamic filenames if needed
            Body=image,
            ContentType='image/jpeg',  # Adjust according to your image type
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Image uploaded successfully!'})
        }

    except ClientError as err:
        message = err.response["Error"]["Message"]
        logger.error("A client error occurred:", message)
        print("A client error occured: " +
              format(message))
    except ImageError as err:
        logger.error(err.message)
        print(err.message)

    else:
        print(
            f"Finished generating image with Amazon Nova Canvas  model {model_id}.")