"""S3 없이 로컬 폴더에 저장하는 개발용 구현. 운영에서는 쓰지 않는다."""

from pathlib import Path

from app.core.storage.base import build_image_key


class LocalImageStorage:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)

    def _path(self, key: str) -> Path:
        path = (self.base_dir / key).resolve()
        if self.base_dir.resolve() not in path.parents:
            raise ValueError("잘못된 저장 키입니다.")
        return path

    def upload_image(self, child_id: int, data: bytes, content_type: str) -> str:
        key = build_image_key(child_id, content_type)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get_presigned_url(self, key: str, expires_in: int | None = None) -> str:
        # 실제 서명은 없고, 로컬 파일 위치를 알려 주는 가짜 주소다.
        return self._path(key).as_uri()

    def delete_image(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
