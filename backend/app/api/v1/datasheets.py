from fastapi import APIRouter

router = APIRouter()

@router.post("/")
async def process_datasheet():
    return {"message": "Datasheet processed successfully"}