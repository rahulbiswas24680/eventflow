from io import BytesIO

import supabase
from django.conf import settings
# from django.core.exceptions import ImproperlyConfigured
# from django.core.files.base import ContentFile
from django.core.files.storage import Storage

supabase_client = supabase.create_client(
    supabase_url=settings.SUPABASE_URL,  # Replace with your Supabase URL
    supabase_key=settings.SUPABASE_API_KEY  # Replace with your Supabase ANON key
    )


class SupabaseStorage(Storage):
    def __init__(self):
        self.supabase_client = supabase_client
        # self.bucket_name = 'eventflow'
        self.bucket_name = settings.SUPABASE_BUCKET

    def _open(self, name, mode='rb'):
        try:
            file_path = self._get_file_path(name)
            data = self.supabase_client.storage.from_(self.bucket_name).download(file_path)
            return BytesIO(data)
        except Exception as e:
            raise IOError(f"Failed to download file from Supabase: {e}")

    def _save(self, name, content):
        print(self.bucket_name)
        try:
            with content as file:  # Use context manager to handle file opening/closing
                file_content = file.read()
                self.supabase_client.storage.from_(self.bucket_name).upload(file=file_content, path=name)
            return name
        except Exception as e:
            raise IOError(f"Failed to upload file to Supabase: {e}")


    def delete(self, name):
        try:
            file_path = self._get_file_path(name)
            self.supabase_client.storage.from_(self.bucket_name).remove(file_path)
        except Exception as e:
            raise IOError(f"Failed to delete file from Supabase: {e}")


    def exists(self, name):
        file_path = self._get_file_path(name)
        try:
            self.supabase_client.storage.from_(self.bucket_name).download(file_path)
            return True
        except:
            return False

    def url(self, name):
        file_path = self._get_file_path(name)
        return self.supabase_client.storage.from_(self.bucket_name).get_public_url(file_path)

    def _get_file_path(self, name):
        return f"{name}"
