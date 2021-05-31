import os


def create_s3_url(s3, key):
    return s3.client('s3').generate_presigned_url(
        'get_object', ExpiresIn=3600,
        Params={'Bucket': os.environ.get("S3_BUCKET"), 'Key': key}
    )
