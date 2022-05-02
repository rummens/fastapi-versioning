from fastapi.routing import APIRouter

from fastapi_versioning import version

router = APIRouter()


@router.get("/greet")
@version(1, 2)
def goodbye() -> str:
    return "Hi there v1.2"


@router.put("/greet")
@version(1, 2)
def goodbye() -> str:
    return "Hi there v1.2"
