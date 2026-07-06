from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, UploadFile


MAX_EXCEL_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_INVOICE_TEXT_UPLOAD_BYTES = 1024 * 1024
MAX_INVOICE_BINARY_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_ATTACHMENT_UPLOAD_BYTES = 10 * 1024 * 1024

EXCEL_EXTENSIONS = {".xlsx", ".xlsm"}
EXCEL_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel.sheet.macroenabled.12",
    "application/zip",
    "application/octet-stream",
}

TEXT_EXTENSIONS = {".txt"}
TEXT_CONTENT_TYPES = {"text/plain", "application/octet-stream"}

INVOICE_BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
INVOICE_BINARY_CONTENT_TYPES = {"image/png", "image/jpeg", "application/pdf", "application/octet-stream"}

ATTACHMENT_EXTENSIONS = EXCEL_EXTENSIONS | TEXT_EXTENSIONS | INVOICE_BINARY_EXTENSIONS
ATTACHMENT_CONTENT_TYPES = EXCEL_CONTENT_TYPES | TEXT_CONTENT_TYPES | INVOICE_BINARY_CONTENT_TYPES


def normalized_extension(file: UploadFile) -> str:
    return Path(file.filename or "").suffix.lower()


def normalized_content_type(file: UploadFile) -> str:
    return (file.content_type or "application/octet-stream").split(";", 1)[0].strip().lower()


async def read_validated_upload(
    file: UploadFile,
    *,
    max_bytes: int,
    allowed_extensions: set[str],
    allowed_content_types: set[str],
    required_magic_prefixes: Iterable[bytes] = (),
) -> bytes:
    extension = normalized_extension(file)
    if extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="不支持的文件扩展名。")

    content_type = normalized_content_type(file)
    if content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail="文件类型与当前上传入口不匹配。")

    content = await _read_with_limit(file, max_bytes=max_bytes)
    magic_prefixes = tuple(required_magic_prefixes)
    if magic_prefixes and not any(content.startswith(prefix) for prefix in magic_prefixes):
        raise HTTPException(status_code=400, detail="文件内容与声明类型不匹配。")
    return content


async def read_invoice_upload(file: UploadFile) -> tuple[bytes, bool]:
    extension = normalized_extension(file)
    if extension in TEXT_EXTENSIONS:
        content = await read_validated_upload(
            file,
            max_bytes=MAX_INVOICE_TEXT_UPLOAD_BYTES,
            allowed_extensions=TEXT_EXTENSIONS,
            allowed_content_types=TEXT_CONTENT_TYPES,
        )
        return content, True

    content = await read_validated_upload(
        file,
        max_bytes=MAX_INVOICE_BINARY_UPLOAD_BYTES,
        allowed_extensions=INVOICE_BINARY_EXTENSIONS,
        allowed_content_types=INVOICE_BINARY_CONTENT_TYPES,
        required_magic_prefixes=_magic_prefixes_for_extension(extension),
    )
    return content, False


async def read_attachment_upload(file: UploadFile) -> bytes:
    extension = normalized_extension(file)
    return await read_validated_upload(
        file,
        max_bytes=MAX_ATTACHMENT_UPLOAD_BYTES,
        allowed_extensions=ATTACHMENT_EXTENSIONS,
        allowed_content_types=ATTACHMENT_CONTENT_TYPES,
        required_magic_prefixes=_magic_prefixes_for_extension(extension),
    )


async def _read_with_limit(file: UploadFile, *, max_bytes: int) -> bytes:
    size = getattr(file, "size", None)
    if isinstance(size, int) and size > max_bytes:
        raise HTTPException(status_code=413, detail="上传文件过大。")

    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_bytes:
            raise HTTPException(status_code=413, detail="上传文件过大。")
        chunks.append(chunk)
    return b"".join(chunks)


def _magic_prefixes_for_extension(extension: str) -> tuple[bytes, ...]:
    if extension in EXCEL_EXTENSIONS:
        return (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
    if extension == ".pdf":
        return (b"%PDF-",)
    if extension == ".png":
        return (b"\x89PNG\r\n\x1a\n",)
    if extension in {".jpg", ".jpeg"}:
        return (b"\xff\xd8\xff",)
    return ()
