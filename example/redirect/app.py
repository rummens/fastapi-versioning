import uvicorn

from fastapi import FastAPI

from example.redirect import v1_0, v1_1, v1_2
from fastapi_versioning import VersionedFastAPI

tags_metadata = [
    {
        "name": "Redirects",
        "description": "bla bla.",
    },
{
        "name": "users",
        "description": "Operations with users. The **login** logic is also here.",
    },
    {
        "name": "items",
        "description": "Manage items. So _fancy_ they have their own docs.",
        "externalDocs": {
            "description": "Items external docs",
            "url": "https://fastapi.tiangolo.com/",
        },
    },
]

app = FastAPI(openapi_tags=tags_metadata)
app.include_router(v1_0.router)
app.include_router(v1_1.router)
app.include_router(v1_2.router)
app = VersionedFastAPI(app,
                       version_format="{major}.{minor}",
                       prefix_format="/v{major}.{minor}",
                       enable_latest=True,
                       redirect_empty_to_version=(1, 0),
                       openapi_tags=tags_metadata
                       )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
