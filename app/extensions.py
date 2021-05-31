"""
To avoid cyclic imports, instantiate extensions here.
Use this module to access them elsewhere in project,
instead using `__init__.py`
"""

from flask_sqlalchemy import SQLAlchemy
import boto3
import os

db = SQLAlchemy()

s3_session = boto3.session.Session(
    aws_access_key_id=os.environ.get("S3_KEY"),
    aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY"),
    region_name=os.environ.get("S3_REGION")
)

from .models import * # noqa