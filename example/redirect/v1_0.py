from fastapi.routing import APIRouter

router = APIRouter()


@router.get("/greet", tags=["users"])
def greet() -> str:
    return "Hello v1.0"
