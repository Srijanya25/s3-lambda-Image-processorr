import boto3
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

s3 = boto3.client('s3')

# Name of the bucket where processed images should be saved
DESTINATION_BUCKET = os.environ.get('DESTINATION_BUCKET', 'srijanya-s3-processed-bucket')

# Resize settings
MAX_WIDTH = 800
JPEG_QUALITY = 70

# Watermark text (set to None to skip watermarking)
WATERMARK_TEXT = "SAMPLE"


def lambda_handler(event, context):
    for record in event['Records']:
        source_bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        # Download the uploaded image into memory
        response = s3.get_object(Bucket=source_bucket, Key=key)
        image_bytes = response['Body'].read()
        image = Image.open(BytesIO(image_bytes))

        # Convert to RGB (handles PNGs with transparency, etc.)
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')

        # Resize while keeping aspect ratio
        if image.width > MAX_WIDTH:
            ratio = MAX_WIDTH / float(image.width)
            new_height = int(image.height * ratio)
            image = image.resize((MAX_WIDTH, new_height))

        # Add a simple text watermark in the bottom-right corner
        if WATERMARK_TEXT:
            draw = ImageDraw.Draw(image)
            text = WATERMARK_TEXT
            # Use default font (no extra font files needed)
            font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            position = (image.width - text_w - 15, image.height - text_h - 15)
            draw.text(position, text, fill=(255, 255, 255), font=font)

        # Save processed image to memory buffer
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=JPEG_QUALITY)
        buffer.seek(0)

        # Upload to destination bucket
        output_key = f"processed-{key}"
        s3.put_object(
            Bucket=DESTINATION_BUCKET,
            Key=output_key,
            Body=buffer,
            ContentType='image/jpeg'
        )

        print(f"Processed {key} -> {output_key} in {DESTINATION_BUCKET}")

    return {
        'statusCode': 200,
        'body': f"Processed {len(event['Records'])} image(s)"
    }