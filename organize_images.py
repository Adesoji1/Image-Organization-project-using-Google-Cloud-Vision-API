import os
import io
from google.cloud import vision
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from config import KEY_PATH, SOURCE_FOLDER_ID, CATEGORIES_TO_FOLDERS

# Authenticate and initialize clients
credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
vision_client = vision.ImageAnnotatorClient(credentials=credentials)
drive_service = build('drive', 'v3', credentials=credentials)

def list_images(folder_id):
    query = f"'{folder_id}' in parents and mimeType contains 'image/'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    return items

def download_image(file_id, file_name):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return file_name

def upload_image(file_name, folder_id):
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_name, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def analyze_image(file_name):
    with open(file_name, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = vision_client.label_detection(image=image)
    labels = response.label_annotations
    categories = [label.description for label in labels]
    return categories

def categorize_and_move_images(folder_id, categories_to_folders):
    images = list_images(folder_id)
    for image in images:
        file_id = image['id']
        file_name = image['name']
        local_path = download_image(file_id, file_name)
        categories = analyze_image(local_path)
        
        # Determine the target folder based on categories
        target_folder_id = None
        for category in categories:
            if category in categories_to_folders:
                target_folder_id = categories_to_folders[category]
                break
        
        if target_folder_id:
            upload_image(local_path, target_folder_id)
            drive_service.files().delete(fileId=file_id).execute()
        os.remove(local_path)

if __name__ == '__main__':
    categorize_and_move_images(SOURCE_FOLDER_ID, CATEGORIES_TO_FOLDERS)
