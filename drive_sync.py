# drive_sync.py
import json
import os
import io
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
import threading
import time

# Configuración
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'
FOLDER_NAME = 'ReciclajeIndustrial'
DATA_FILE = 'reciclaje_data.json'
CAJA_FILE = 'caja_diaria.json'

class GoogleDriveSync:
    def __init__(self):
        self.service = None
        self.folder_id = None
        self.connected = False
        self.last_sync = None
        self.sync_in_progress = False
        
    def connect(self):
        """Conecta con Google Drive usando las credenciales"""
        try:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"❌ No se encuentra el archivo {CREDENTIALS_FILE}")
                print("📌 Asegúrate de haber descargado el archivo JSON de Google Cloud")
                return False
            
            credentials = service_account.Credentials.from_service_account_file(
                CREDENTIALS_FILE, scopes=SCOPES
            )
            self.service = build('drive', 'v3', credentials=credentials)
            
            self.folder_id = self._get_or_create_folder()
            
            if self.folder_id:
                self.connected = True
                print("✅ Conectado a Google Drive exitosamente")
                return True
            else:
                print("❌ No se pudo crear/acceder a la carpeta en Google Drive")
                return False
                
        except Exception as e:
            print(f"❌ Error al conectar con Google Drive: {e}")
            return False
    
    def _get_or_create_folder(self):
        try:
            results = self.service.files().list(
                q=f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                return folders[0]['id']
            
            file_metadata = {
                'name': FOLDER_NAME,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            print(f"📁 Carpeta '{FOLDER_NAME}' creada en Google Drive")
            return folder.get('id')
            
        except Exception as e:
            print(f"❌ Error al buscar/crear carpeta: {e}")
            return None
    
    def _upload_file(self, file_name, data, is_json=True):
        try:
            if not self.service:
                return False
            
            results = self.service.files().list(
                q=f"name='{file_name}' and '{self.folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if is_json:
                content = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
            else:
                content = data.encode('utf-8') if isinstance(data, str) else data
            
            media = MediaIoBaseUpload(
                io.BytesIO(content),
                mimetype='application/json' if is_json else 'text/plain',
                resumable=True
            )
            
            if files:
                file_id = files[0]['id']
                self.service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                print(f"✅ Archivo '{file_name}' actualizado en Google Drive")
            else:
                file_metadata = {
                    'name': file_name,
                    'parents': [self.folder_id]
                }
                self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                print(f"✅ Archivo '{file_name}' creado en Google Drive")
            
            return True
            
        except Exception as e:
            print(f"❌ Error al subir {file_name}: {e}")
            return False
    
    def _download_file(self, file_name, is_json=True):
        try:
            if not self.service:
                return None
            
            results = self.service.files().list(
                q=f"name='{file_name}' and '{self.folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                return None
            
            file_id = files[0]['id']
            request = self.service.files().get_media(fileId=file_id)
            file_data = io.BytesIO()
            downloader = MediaIoBaseDownload(file_data, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            file_data.seek(0)
            
            if is_json:
                return json.loads(file_data.read().decode('utf-8'))
            else:
                return file_data.read().decode('utf-8')
                
        except Exception as e:
            print(f"❌ Error al descargar {file_name}: {e}")
            return None
    
    def sync_data(self, data=None):
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            if data is not None:
                result = self._upload_file(DATA_FILE, data)
                if result:
                    self.last_sync = datetime.now()
                return result
            else:
                return self._download_file(DATA_FILE)
        except Exception as e:
            print(f"❌ Error al sincronizar datos: {e}")
            return None
    
    def sync_caja(self, data=None):
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            if data is not None:
                return self._upload_file(CAJA_FILE, data)
            else:
                return self._download_file(CAJA_FILE)
        except Exception as e:
            print(f"❌ Error al sincronizar caja: {e}")
            return None
    
    def upload_backup(self, data):
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"reciclaje_data_backup_{timestamp}.json"
            
            results = self.service.files().list(
                q=f"name contains 'reciclaje_data_backup_' and '{self.folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id, name, createdTime)'
            ).execute()
            
            backups = results.get('files', [])
            
            if len(backups) >= 10:
                backups.sort(key=lambda x: x['name'], reverse=True)
                for backup in backups[9:]:
                    self.service.files().delete(fileId=backup['id']).execute()
            
            return self._upload_file(backup_name, data)
            
        except Exception as e:
            print(f"❌ Error al subir backup: {e}")
            return False
    
    def list_backups(self):
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            results = self.service.files().list(
                q=f"name contains 'reciclaje_data_backup_' and '{self.folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id, name, createdTime)',
                orderBy='createdTime desc'
            ).execute()
            
            return results.get('files', [])
            
        except Exception as e:
            print(f"❌ Error al listar backups: {e}")
            return []
    
    def get_sync_status(self):
        if not self.connected:
            return "❌ No conectado"
        if self.last_sync:
            return f"✅ Sincronizado: {self.last_sync.strftime('%H:%M:%S')}"
        return "✅ Conectado (sin sincronizar)"
    
    def force_reconnect(self):
        self.connected = False
        self.service = None
        return self.connect()

drive_sync = GoogleDriveSync()