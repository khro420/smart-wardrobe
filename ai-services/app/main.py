from fastapi import FastAPI, UploadFile, File
import os
import uuid
import cv2

from app.cv.pipeline import GarmentPipeline

app = FastAPI()

pipeline = GarmentPipeline("../models/cv/best.pt")


@app.post("/detect")
async def detect(file: UploadFile = File(...)):

    os.makedirs("static/uploads", exist_ok=True)

    image_path = f"static/uploads/{uuid.uuid4()}.jpg"

    with open(image_path, "wb") as f:
        f.write(await file.read())

    results = pipeline.process(image_path)

    return {
        "num_garments": len(results),
        "results": results
    }