import uuid

from app.common.exceptions import BadRequestException
from app.config import settings
from app.evidence.schemas import UploadURLResponse
from app.infrastructure.minio import ensure_bucket_exists, get_s3_client


class EvidenceService:
    def __init__(self):
        # Ensure the bucket exists
        try:
            ensure_bucket_exists()
        except Exception:
            pass  # Suppress errors if minio service is not reachable during tests or typing check

    async def generate_upload_url(
        self, task_id: uuid.UUID, file_name: str, content_type: str
    ) -> UploadURLResponse:
        # Validate content type is image or video
        allowed_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "video/mp4",
            "video/mpeg",
            "video/quicktime",
        ]
        if content_type.lower() not in allowed_types:
            raise BadRequestException(
                "Invalid content type. Only images and videos are allowed."
            )

        s3_client = get_s3_client()
        unique_id = uuid.uuid4()
        evidence_key = f"{task_id}/{unique_id}-{file_name}"

        # Generate presigned PUT URL
        try:
            upload_url = s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": settings.MINIO_BUCKET,
                    "Key": evidence_key,
                    "ContentType": content_type,
                },
                ExpiresIn=3600,  # 1 hour expiration
            )
        except Exception as e:
            raise BadRequestException(f"Failed to generate upload URL: {str(e)}")

        # Construct download URL (public access URL)
        protocol = "https" if settings.MINIO_SECURE else "http"
        download_url = f"{protocol}://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{evidence_key}"

        return UploadURLResponse(
            upload_url=upload_url,
            download_url=download_url,
            evidence_key=evidence_key,
        )
