"""AWS S3 구현. 버킷은 비공개로 두고, 조회는 presigned URL로만 허용한다.

자격 증명은 코드에 넣지 않는다. EC2에서는 인스턴스 IAM 역할을, 로컬에서는 AWS CLI 프로필(~/.aws)을 boto3가 자동으로 읽는다.
"""

from typing import Any

from app.core.storage.base import build_image_key


class S3ImageStorage:
    def __init__(self, bucket: str, region: str, default_expires_in: int, client: Any | None = None) -> None:
        if not bucket:
            raise ValueError("S3_BUCKET 환경변수가 비어 있습니다.")
        self.bucket = bucket
        self.default_expires_in = default_expires_in
        if client is None:
            import boto3  # STORAGE_BACKEND=s3일 때만 필요

            client = boto3.client("s3", region_name=region)
        self.client = client

    def upload_image(self, child_id: int, data: bytes, content_type: str) -> str:
        key = build_image_key(child_id, content_type)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
        return key

    def get_image(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except self.client.exceptions.NoSuchKey as err:
            raise FileNotFoundError(key) from err
        data: bytes = response["Body"].read()
        return data

    def get_presigned_url(self, key: str, expires_in: int | None = None) -> str:
        url: str = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in or self.default_expires_in,
        )
        return url

    def delete_image(self, key: str) -> None:
        # S3 delete_object는 키가 없어도 성공한다.
        self.client.delete_object(Bucket=self.bucket, Key=key)
