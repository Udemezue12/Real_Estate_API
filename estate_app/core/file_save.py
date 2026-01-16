# import os
# from file_configs import UPLOAD_DIR
# from fastapi import UploadFile, HTTPException
# import aiofiles


# async def save_uploaded_file(file: UploadFile) -> str:
#     if not file.filename.lower().endswith((".pdf", ".docx")):
#         raise HTTPException(
#             status_code=400, detail="Only PDF or DOCX Files are allowed"
#         )
#     file_path = os.path.join(UPLOAD_DIR, file.filename)

#     async with aiofiles.open(file_path, "wb") as out_file:
#         while True:
#             content = await file.read(1024)
#             if not content:
#                 break
#             await out_file.write(content)

#     return file_path
