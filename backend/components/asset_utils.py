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
"""Utilities for managing assets.

This module provides helper functions for uploading and managing various asset
types, including images, videos, and audio.
"""
import logging
import types
from components import firestore_crud
from components import gcs_storage
import constants
from mocks import asset_mocks
from models import asset_models
from models import data_models
import settings


logger = logging.getLogger(__name__)
env_settings = settings.EnvSettings()


def upload_image_asset(
    input_data: asset_models.ImageUploadInput,
) -> str:
  """Upload the image to Google Cloud Storage and write metadata to Firestore.

  Args:
    input_data: The image and relevant metadata.

  Returns:
    The Firestore document ID of the created image.
  """
  logger.info('Uploading image asset, %s', input_data)

  if env_settings.use_mocks:
    logger.warning('Returning mock responses.')
    return input_data.image_id

  gcs_file_name = f'{input_data.image_id}{input_data.get_file_extension()}'
  gcs_file_path = f'{constants.StoragePaths.IMAGES}/{gcs_file_name}'
  full_gcs_file_path = (
      f'gs://{env_settings.google_cloud_storage_bucket_name}/{gcs_file_path}'
  )

  gcs_storage.write_to_gcs(
      file_content=input_data.image.file.read(),
      bucket_name=env_settings.google_cloud_storage_bucket_name,
      file_name=gcs_file_path,
  )

  image_data = data_models.Image(
      bucket_name=env_settings.google_cloud_storage_bucket_name,
      file_path=gcs_file_path,
      file_name=gcs_file_name,
      original_file_name=input_data.image.filename,
      full_gcs_path=full_gcs_file_path,
      source=input_data.source.value,
      image_name=input_data.image_name,
      context=input_data.context,
  )
  document_id = firestore_crud.create_document(
      collection_name=constants.FirestoreCollections.IMAGES,
      document_id=input_data.image_id,
      data=image_data,
      database_name=env_settings.firestore_db_name,
  )
  # TODO: b/396329773 - update session document if a session_id is provided.
  return document_id


def get_image_metadata_with_signed_url(
    image_id: str,
    firestore_utils: types.ModuleType | None = None,
    storage_utils: types.ModuleType | None = None,
    mocks_module: types.ModuleType | None = None,
) -> asset_models.ImageMetadataResult | None:
  """Fetches image metadata from Firestore and generates a signed URL.

  Args:
    image_id: The ID of the image document in Firestore.
    firestore_utils: The module for Firestore operations (defaults to
      firestore_crud). Primarily, used for dependency injection in testing.
    storage_utils: The module for GCS operations (defaults to gcs_storage).
      Primarily, used for dependency injection in testing.
    mocks_module: The module used for pulling the mocks (defaults to
      asset_mocks). Primarily, used for dependency injection in testing.

  Returns:
    The image metadata with a signed URL, or None if not found.
  """
  if env_settings.use_mocks:
    mocks_module = mocks_module or asset_mocks
    return mocks_module.mock_get_image_metadata_with_signed_url(image_id)

  firestore_utils = firestore_utils or firestore_crud
  storage_utils = storage_utils or gcs_storage

  image_doc = firestore_utils.get_document(
      collection_name=constants.FirestoreCollections.IMAGES,
      document_id=image_id,
      model_type=data_models.Image,
      database_name=env_settings.firestore_db_name,
  )
  if not image_doc:
    return None

  image_metadata_response = asset_models.ImageMetadataResult(
      **image_doc.model_dump()
  )
  image_metadata_response.generate_signed_url(storage_utils)
  return image_metadata_response
