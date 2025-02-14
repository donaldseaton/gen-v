# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The model definitions for the assets."""

import datetime
import os
import types

from components import gcs_storage
import constants
import fastapi
from models import api_models
import pydantic


class ImageUploadInput(pydantic.BaseModel):
  """Input model for uploading an image asset.

  Attributes:
    image: The image file to be uploaded.
    source: The source of the image.
    session_id: If this belongs to a session, provide the session ID, else if
      None it will be a global asset.
    image_name: Optional user-provided name for the image.
    context: Optional context description for the image.
    image_id: Optional provide an ID to use for the image, else it is randomly
      generated.
  """

  image: fastapi.UploadFile = fastapi.File(...)
  source: api_models.ImageSource
  session_id: str | None = None
  image_name: str | None = None
  context: str | None = None
  image_id: str = pydantic.Field(default_factory=lambda: os.urandom(8).hex())

  @classmethod
  @pydantic.field_validator('image')
  def validate_image_type(cls, value):
    _, extension = os.path.splitext(value.filename)
    if extension.lower() not in constants.ALLOWED_IMAGE_EXTENSIONS:
      raise ValueError('Invalid image type')
    return value

  def get_file_extension(self) -> str:
    """Gets the file extension from the image_file.

    Returns:
      The file extension (including the leading dot), or an empty string
        if the filename is invalid or has no extension.
    """
    _, extension = os.path.splitext(self.image.filename)
    return extension.lower()


class ImageMetadataResult(pydantic.BaseModel):
  """Represents the metadata of an image with signed URL.

  Attributes:
    bucket_name: The name of the Google Cloud Storage bucket where the image is
      stored.
    file_path: The path on the bucket to the image file.
    file_name: The original filename of the uploaded image.
    original_file_name: The name of the original file.
    full_gcs_path: The full Google Cloud Storage path to the image, e.g.
      "gs://path/to/image/my-image.png".
    source: The source of the image (e.g., "Brand", "Imagen"). Stored as the
      string value of the ImageSource enum.
    image_name: Optional user-provided name for the image.
    context: Optional context description for the image.
    date_created: The datetime that this was created.
    signed_url: A signed URL to the file on GCS.
  """

  bucket_name: str
  file_path: str
  file_name: str
  original_file_name: str
  full_gcs_path: str
  source: str
  image_name: str | None = None
  context: str | None = None
  date_created: datetime.datetime
  signed_url: str = ''

  def generate_signed_url(
      self, storage_utils: types.ModuleType | None = None
  ) -> None:
    """Generates and adds the signed URL to this object.

    Args:
      storage_utils: The module for GCS operations (defaults to gcs_storage).
        Primarily, used for dependency injection in testing.
    """
    storage_utils = storage_utils or gcs_storage
    self.signed_url = storage_utils.get_signed_url_from_gcs(
        bucket_name=self.bucket_name, file_name=self.file_path
    )
