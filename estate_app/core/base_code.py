from base64 import b64decode, urlsafe_b64encode

from fastapi import HTTPException


def base64url_encode(data) -> str:
    try:
        if isinstance(data, str):
            try:
                data = b64decode(data)
            except Exception:
                try:
                    data = bytes.fromhex(data)
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail="Data must be a base64 string, hex string, or raw bytes.",
                    )

        if not isinstance(data, bytes):
            raise HTTPException(
                status_code=400,
                detail="Input must be bytes, base64 string, or hex string.",
            )

        return urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Encoding error: {str(e)}")