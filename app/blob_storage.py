import os, uuid
import imghdr
from PIL import Image
from io import BytesIO
import ulid
import base64
import re

# FastAPI
from fastapi import HTTPException

# Azure
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

from app.config import settings

"""
Azure Blob Storageを使用して画像を保存する
"""

COMPRESS_QUALITY=50

# Blob Storageへのアクセス認証
try:
    # Quickstart code goes here
    # Create the BlobServiceClient object
    blob_service_client = BlobServiceClient.from_connection_string(settings.connect_str)

except Exception as ex:
    print('Exception:')
    print(ex)

def upload_to_blob(binary:bytes) -> str:
    try:
        image_type = imghdr.what(None,h=binary)
        if not(image_type=="png" or image_type=="jpeg"):
            raise HTTPException(415,"Invalid File Type:png or jpeg")
        
        im=Image.open(BytesIO(binary))
        if image_type=="png":
            im = im.convert('RGB')
        im_io=BytesIO()
        im.save(im_io, 'JPEG', quality = COMPRESS_QUALITY)
        
        filename=ulid.new().str+".jpg"
        blob_client = blob_service_client.get_blob_client(container=settings.container_name, blob=filename)

        # Upload the blob data - default blob type is BlockBlob
        blob_client.upload_blob(im_io.getvalue(), blob_type="BlockBlob")
    except:
        raise HTTPException(500, "Internal Server Error")
    file_url = f"{settings.container_name}/{filename}"
    return file_url

def upload_to_blob_public(binary:bytes) -> str:
    try:
        image_type = imghdr.what(None,h=binary)
        if not(image_type=="png" or image_type=="jpeg"):
            raise HTTPException(415,"Invalid File Type:png or jpeg")
        
        im=Image.open(BytesIO(binary))
        if image_type=="png":
            im = im.convert('RGB')
        im_io=BytesIO()
        im.save(im_io, 'JPEG', quality = COMPRESS_QUALITY)
        
        filename=ulid.new().str+".jpg"
        blob_client = blob_service_client.get_blob_client(container=settings.container_name, blob=filename)

        # Upload the blob data - default blob type is BlockBlob
        blob_client.upload_blob(im_io.getvalue(), blob_type="BlockBlob")
    except:
        raise HTTPException(500,"Internal Server Error")
    
    file_url = f"https://quaintstorage.blob.core.windows.net/{settings.container_name}/{filename}"
    return file_url

def delete_image(image_url:str) -> None:
    try:
        file_name = re.findall(f'https://quaintstorage.blob.core.windows.net/{settings.container_name}/(.*)',image_url)
        blob_client = blob_service_client.get_blob_client(container=settings.container_name, blob=file_name[0])
        blob_client.delete_blob()
    except:
        raise HTTPException(500,"Internal Server Error")