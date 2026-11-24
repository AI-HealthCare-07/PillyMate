import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.storage.base import build_image_key
from app.core.storage.local import LocalImageStorage
from app.core.storage.s3 import S3ImageStorage


class TestImageKey:
    def test_key_follows_spec_rule(self) -> None:
        assert re.fullmatch(r"prescriptions/3/[0-9a-f]{32}\.jpg", build_image_key(3, "image/jpeg"))
        assert build_image_key(3, "image/png").endswith(".png")

    def test_unsupported_type_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            build_image_key(3, "image/heic")


class TestLocalImageStorage:
    def test_upload_url_delete(self, tmp_path: Path) -> None:
        storage = LocalImageStorage(base_dir=str(tmp_path))
        key = storage.upload_image(child_id=7, data=b"img", content_type="image/jpeg")
        stored = tmp_path / key
        assert stored.read_bytes() == b"img"
        assert storage.get_image(key) == b"img"
        assert storage.get_presigned_url(key).startswith("file://")
        storage.delete_image(key)
        assert not stored.exists()
        storage.delete_image(key)  # 이미 없어도 오류 없음
        with pytest.raises(FileNotFoundError):
            storage.get_image(key)

    def test_rejects_path_outside_base_dir(self, tmp_path: Path) -> None:
        storage = LocalImageStorage(base_dir=str(tmp_path))
        with pytest.raises(ValueError):
            storage.delete_image("../outside.jpg")


class TestS3ImageStorage:
    def test_calls_boto3_client(self) -> None:
        client = MagicMock()
        client.generate_presigned_url.return_value = "https://signed"
        storage = S3ImageStorage(bucket="pilly-bucket", region="ap-northeast-2", default_expires_in=600, client=client)

        key = storage.upload_image(child_id=1, data=b"img", content_type="image/png")
        client.put_object.assert_called_once()
        assert client.put_object.call_args.kwargs["Key"] == key

        client.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=b"img"))}
        assert storage.get_image(key) == b"img"
        client.get_object.assert_called_once_with(Bucket="pilly-bucket", Key=key)

        assert storage.get_presigned_url(key) == "https://signed"
        assert client.generate_presigned_url.call_args.kwargs["ExpiresIn"] == 600

        storage.delete_image(key)
        client.delete_object.assert_called_once_with(Bucket="pilly-bucket", Key=key)

    def test_empty_bucket_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            S3ImageStorage(bucket="", region="ap-northeast-2", default_expires_in=600, client=MagicMock())
