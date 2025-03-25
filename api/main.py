import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import qrcode
import os
from io import BytesIO
from azure.storage.blob import BlobServiceClient, ContentSettings  # Import ContentSettings

# Loading Environment variable (Azure Storage Connection String and Container Name)
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Allowing CORS for local testing
origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Azure Blob Storage Configuration
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = os.getenv("AZURE_CONTAINER_NAME", "qrcodes")

# Create a BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Get or create the container
container_client = blob_service_client.get_container_client(container_name)
try:
    container_client.create_container()  # Create the container if it doesn't exist
except Exception as e:
    # If the container already exists, ignore the error
    if "ContainerAlreadyExists" not in str(e):
        raise HTTPException(status_code=500, detail=f"Failed to create container: {str(e)}")


@app.post("/generate-qr/")
async def generate_qr(url: str):
    # Generate QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Save QR Code to BytesIO object
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    # Generate file name for Azure Blob Storage
    file_name = f"qr_codes/{url.split('//')[-1]}.png"

    try:
        # Upload to Azure Blob Storage
        blob_client = container_client.get_blob_client(file_name)
        blob_client.upload_blob(
            img_byte_arr,
            content_settings=ContentSettings(content_type="image/png")
        )

        # Generate the Azure Blob Storage URL
        blob_url = blob_client.url
        return {"qr_code_url": blob_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
