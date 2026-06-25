from fastapi import FastAPI, UploadFile, File
import os
import uuid

from app.cv.pipeline import GarmentPipeline

app = FastAPI(title="Garment Attribute Extraction API", version="2.0")

pipeline = GarmentPipeline("../models/cv/best.pt")


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    os.makedirs("static/uploads", exist_ok=True)

    image_path = f"static/uploads/{uuid.uuid4()}.jpg"

    with open(image_path, "wb") as f:
        f.write(await file.read())

    results = pipeline.process(image_path)

    return results