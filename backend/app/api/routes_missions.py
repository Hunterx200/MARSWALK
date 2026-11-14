"""Mission planning and retrieval endpoints."""
from fastapi import APIRouter
from app.schemas.mission import MissionCreateRequest, MissionResponse
from app.services.mission_service import mission_service

router = APIRouter(tags=["Missions"])


@router.post("/missions", response_model=MissionResponse, status_code=201)
async def create_mission(request: MissionCreateRequest):
    """
    Create a new mission plan with automated report synthesis.
    Stores mission in in-memory storage for MVP.
    """
    return mission_service.create_mission(request)


@router.get("/missions/{mission_id}", response_model=MissionResponse)
async def get_mission(mission_id: str):
    """
    Retrieve an existing mission plan by ID.
    Returns 404 if the mission is not found.
    """
    return mission_service.get_mission(mission_id)
