"""Private upload storage for B9.2. Only generated opaque keys enter this adapter."""
from pathlib import Path
import re
from uuid import uuid4

import httpx

from app.core.config import Settings


class StorageUnavailable(RuntimeError):
    pass


class ResourceStorage:
    def __init__(self, settings: Settings):
        self.settings = settings

    def new_key(self, suffix: str) -> str:
        return f"resource-uploads/{uuid4().hex}{suffix}"

    @staticmethod
    def checked_key(key: str) -> str:
        if not re.fullmatch(r"resource-uploads/[0-9a-f]{32}\.(?:jpg|jpeg|png|webp|gif|mp3|m4a|mp4|webm|html|htm)", key):
            raise StorageUnavailable("invalid_storage_key")
        return key

    def local_path(self, key: str, *, for_write: bool = False) -> Path:
        key = self.checked_key(key)
        suffix = Path(key).suffix
        folder = 'interactive' if suffix in {'.html', '.htm'} else 'images' if suffix in {'.jpg', '.jpeg', '.png', '.webp', '.gif'} else 'media'
        root = Path(self.settings.resource_local_dir).resolve()
        target = root / folder / Path(key).name
        if folder == 'interactive':
            # Keep opaque catalogue keys stable when local activities have named folders.
            matches = list((root / folder).glob(f'*/{Path(key).name}'))
            if target.is_file():
                matches.append(target)
            if len(matches) > 1:
                raise StorageUnavailable('duplicate_interactive_asset')
            if matches:
                target = matches[0]
                if not target.resolve().is_relative_to(root / folder):
                    raise StorageUnavailable('invalid_interactive_path')
            else:
                target = root / folder / Path(key).stem / Path(key).name
        # Logical keys and old flat local uploads remain compatible.
        legacy = root / key
        return legacy if not for_write and not target.is_file() and legacy.is_file() else target

    def read_document(self, key: str, limit: int) -> bytes:
        key = self.checked_key(key)
        if not key.endswith((".html", ".htm")):
            raise StorageUnavailable("invalid_interactive_key")
        try:
            if self.settings.resource_storage_backend == "local":
                with self.local_path(key).open("rb") as stream:
                    data = stream.read(limit + 1)
            else:
                secret = self.settings.supabase_secret_key or self.settings.supabase_service_role_key
                if not self.settings.supabase_url or not secret or not self.settings.resource_storage_bucket:
                    raise StorageUnavailable("resource_storage_unconfigured")
                url = f"{self.settings.supabase_url}/storage/v1/object/{self.settings.resource_storage_bucket}/{key}"
                token = secret.get_secret_value()
                data = bytearray()
                with httpx.Client(timeout=15, follow_redirects=False) as client:
                    with client.stream("GET", url, headers={"apikey": token, "Authorization": f"Bearer {token}"}) as response:
                        if response.status_code != 200:
                            raise StorageUnavailable("resource_asset_missing")
                        for chunk in response.iter_bytes(65536):
                            data.extend(chunk)
                            if len(data) > limit:
                                raise StorageUnavailable("interactive_document_too_large")
            if len(data) > limit:
                raise StorageUnavailable("interactive_document_too_large")
            return bytes(data)
        except (OSError, httpx.HTTPError) as exc:
            raise StorageUnavailable("resource_storage_unavailable") from exc

    def download_to(self, key: str, destination: Path, limit: int) -> None:
        """Bounded server-side asset retrieval; bytes never pass through a browser BFF."""
        key = self.checked_key(key)
        size = 0
        try:
            with destination.open("wb") as out:
                if self.settings.resource_storage_backend == "local":
                    with self.local_path(key).open("rb") as source:
                        while chunk := source.read(65536):
                            size += len(chunk)
                            if size > limit:
                                raise StorageUnavailable("resource_asset_too_large")
                            out.write(chunk)
                else:
                    secret = self.settings.supabase_secret_key or self.settings.supabase_service_role_key
                    if not self.settings.supabase_url or not secret or not self.settings.resource_storage_bucket:
                        raise StorageUnavailable("resource_storage_unconfigured")
                    token = secret.get_secret_value()
                    url = f"{self.settings.supabase_url}/storage/v1/object/{self.settings.resource_storage_bucket}/{key}"
                    with httpx.Client(timeout=120, follow_redirects=False) as client:
                        with client.stream("GET", url, headers={"apikey": token, "Authorization": "Bearer " + token}) as response:
                            if response.status_code != 200:
                                raise StorageUnavailable("resource_asset_missing")
                            for chunk in response.iter_bytes(65536):
                                size += len(chunk)
                                if size > limit:
                                    raise StorageUnavailable("resource_asset_too_large")
                                out.write(chunk)
        except (OSError, httpx.HTTPError) as exc:
            raise StorageUnavailable("resource_storage_unavailable") from exc

    def put(self, key: str, source: Path, mime_type: str) -> None:
        key = self.checked_key(key)
        if self.settings.resource_storage_backend == "local":
            target = self.local_path(key, for_write=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            created = False
            try:
                with open(source, "rb") as src, open(target, "xb") as dst:
                    created = True
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
            except OSError as exc:
                if created: target.unlink(missing_ok=True)
                raise StorageUnavailable("resource_storage_unavailable") from exc
            return
        secret = self.settings.supabase_secret_key or self.settings.supabase_service_role_key
        if not self.settings.supabase_url or not secret or not self.settings.resource_storage_bucket:
            raise StorageUnavailable("resource_storage_unconfigured")
        url = f"{self.settings.supabase_url}/storage/v1/object/{self.settings.resource_storage_bucket}/{key}"
        token = secret.get_secret_value()
        try:
            with open(source, "rb") as stream, httpx.Client(timeout=120, follow_redirects=False) as client:
                response = client.post(url, headers={"apikey": token, "Authorization": f"Bearer {token}",
                    "Content-Type": mime_type, "x-upsert": "false"}, content=stream)
            if response.status_code not in (200, 201):
                raise StorageUnavailable("resource_storage_unavailable")
        except (OSError, httpx.HTTPError) as exc:
            raise StorageUnavailable("resource_storage_unavailable") from exc

    def delete(self, key: str) -> None:
        key = self.checked_key(key)
        if self.settings.resource_storage_backend == "local":
            self.local_path(key).unlink(missing_ok=True)
            return
        secret = self.settings.supabase_secret_key or self.settings.supabase_service_role_key
        if not self.settings.supabase_url or not secret or not self.settings.resource_storage_bucket:
            return
        token = secret.get_secret_value()
        url = f"{self.settings.supabase_url}/storage/v1/object/{self.settings.resource_storage_bucket}"
        try:
            with httpx.Client(timeout=15, follow_redirects=False) as client:
                client.request("DELETE", url, headers={"apikey": token, "Authorization": f"Bearer {token}"},
                    json={"prefixes": [key]})
        except httpx.HTTPError:
            pass


    def exists(self, key: str) -> bool:
        key = self.checked_key(key)
        if self.settings.resource_storage_backend == "local":
            return self.local_path(key).is_file()
        secret = self.settings.supabase_secret_key or self.settings.supabase_service_role_key
        if not self.settings.supabase_url or not secret or not self.settings.resource_storage_bucket:
            raise StorageUnavailable("resource_storage_unconfigured")
        token = secret.get_secret_value()
        url = f"{self.settings.supabase_url}/storage/v1/object/{self.settings.resource_storage_bucket}/{key}"
        try:
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                response = client.head(url, headers={"apikey": token, "Authorization": f"Bearer {token}"})
            # Supabase's storage-js exists() treats missing HEADs as 400 or 404.
            if response.status_code in (400, 404):
                return False
            if response.status_code != 200:
                raise StorageUnavailable("resource_storage_unavailable")
            return True
        except httpx.HTTPError as exc:
            raise StorageUnavailable("resource_storage_unavailable") from exc

    def signed_url(self, resource_id, key: str, expires: int, signature: str, *, thumbnail: bool = False) -> str:
        key = self.checked_key(key)
        if self.settings.resource_storage_backend == "local":
            origin = self.settings.resource_local_delivery_origin.rstrip("/")
            return f"{origin}/api/v1/resources/{resource_id}/content?expires={expires}&signature={signature}" + ("&thumbnail=true" if thumbnail else "")
        secret = self.settings.supabase_secret_key or self.settings.supabase_service_role_key
        if not self.settings.supabase_url or not secret or not self.settings.resource_storage_bucket:
            raise StorageUnavailable("resource_storage_unconfigured")
        token = secret.get_secret_value()
        url = f"{self.settings.supabase_url}/storage/v1/object/sign/{self.settings.resource_storage_bucket}/{key}"
        try:
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                response = client.post(url, headers={"apikey": token, "Authorization": f"Bearer {token}"},
                                       json={"expiresIn": 300})
            if response.status_code != 200:
                raise StorageUnavailable("resource_storage_unavailable")
            signed = response.json().get("signedURL")
            if not isinstance(signed, str) or not signed.startswith("/object/sign/"):
                raise StorageUnavailable("resource_storage_unavailable")
            return self.settings.supabase_url + "/storage/v1" + signed
        except (httpx.HTTPError, ValueError) as exc:
            raise StorageUnavailable("resource_storage_unavailable") from exc
