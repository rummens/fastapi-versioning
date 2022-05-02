from collections import defaultdict
from typing import Any, Callable, Dict, List, Tuple, TypeVar, cast, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.openapi.utils import get_openapi
from starlette.routing import BaseRoute

CallableT = TypeVar("CallableT", bound=Callable[..., Any])


def version(major: int, minor: int = 0) -> Callable[[CallableT], CallableT]:
    def decorator(func: CallableT) -> CallableT:
        func._api_version = (major, minor)  # type: ignore
        return func

    return decorator


def version_to_route(
        route: BaseRoute,
        default_version: Tuple[int, int],
) -> Tuple[Tuple[int, int], APIRoute]:
    api_route = cast(APIRoute, route)
    version = getattr(api_route.endpoint, "_api_version", default_version)
    return version, api_route


def doc_endpoint_response() -> HTTPException:
    raise HTTPException(status_code=400, detail={"msg": "Endpoint only exits for documentation purposes. "
                                                        "It has no logic."})


def remove_non_present_openapi_tags(tags: List[Dict[str, Any]], routes: List[BaseRoute]) -> List[Dict]:
    return_tags = []
    for tag in tags:
        for route in routes:
            if hasattr(route, "tags") and tag["name"] in route.tags:
                return_tags.append(tag)

    return return_tags


OPENAPI_TAGS_VERSIONED_ENDPOINTS = [
    {
        "name": "Redirects",
        "description": "Doc Endpoints to show which automatic Redirects are active. Redirects will add new routes "
                       "automatically based on given ruleset and version.",
    },
    {
        "name": "Versions",
        "description": "List of versions current available.",
    },
    {
        "name": "Documentations",
        "description": "Link to the different documentation styles (Swagger and Redoc) for each version.",
    },
]


def VersionedFastAPI(
        app: FastAPI,
        version_format: str = "{major}.{minor}",
        prefix_format: str = "/v{major}_{minor}",
        default_version: Tuple[int, int] = (1, 0),
        enable_latest: bool = False,
        redirect_empty_to_version: Tuple[int, int] = None,
        openapi_tags: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
) -> FastAPI:
    parent_app = FastAPI(
        title=app.title,
        openapi_tags=None,
        **kwargs,
    )
    version_route_mapping: Dict[Tuple[int, int], List[APIRoute]] = defaultdict(
        list
    )
    version_routes = [
        version_to_route(route, default_version) for route in app.routes
    ]
    doc_endpoints: List[APIRoute] = []

    openapi_tags = openapi_tags if openapi_tags is not None else []
    openapi_tags += OPENAPI_TAGS_VERSIONED_ENDPOINTS

    for version, route in version_routes:
        version_route_mapping[version].append(route)

    unique_routes = {}
    versions = sorted(version_route_mapping.keys())
    for version in versions:
        major, minor = version
        prefix = prefix_format.format(major=major, minor=minor)
        semver = version_format.format(major=major, minor=minor)
        versioned_app = FastAPI(
            title=app.title,
            description=app.description,
            version=semver,
            openapi_tags=None
        )
        for route in version_route_mapping[version]:
            for method in route.methods:
                unique_routes[route.path + "|" + method] = route
        for route in unique_routes.values():
            versioned_app.router.routes.append(route)
        versioned_app.openapi_tags = remove_non_present_openapi_tags(openapi_tags, versioned_app.routes)
        parent_app.mount(prefix, versioned_app)

        # also add routes under / if current version is the one that should be redirected to
        if redirect_empty_to_version is not None and redirect_empty_to_version == version:
            # add all routes of current version into parent as well but without prefix
            for route in unique_routes.values():
                parent_app.router.routes.append(route)

            # add dummy endpoint for docs
            doc_endpoints.append(APIRoute("/*", doc_endpoint_response, name="No Version", tags=["Redirects"],
                                          description="Requests made to endpoint without version (i.e. directly to "
                                                      "`/*`) will be redirected to version %s (i.e. `/%s/*`)"
                                                      % (semver, semver)))

        # add dummy endpoint for docs
        doc_endpoints.append(APIRoute(
            f"{prefix}/openapi.json", doc_endpoint_response, name=semver, tags=["Versions"]
        ))
        doc_endpoints.append(APIRoute(f"{prefix}/docs", doc_endpoint_response, name="%s Swagger" % semver, tags=["Documentations"]))
        doc_endpoints.append(APIRoute(f"{prefix}/redoc", doc_endpoint_response, name="%s Redoc" % semver, tags=["Documentations"]))

    if enable_latest:
        prefix = "/latest"
        major, minor = version
        semver = version_format.format(major=major, minor=minor)
        versioned_app = FastAPI(
            title=app.title,
            description=app.description,
            version=semver,
            openapi_tags=None
        )
        for route in unique_routes.values():
            versioned_app.router.routes.append(route)
        versioned_app.openapi_tags = remove_non_present_openapi_tags(openapi_tags, versioned_app.routes)
        parent_app.mount(prefix, versioned_app)

        doc_endpoints.append(APIRoute("/latest/*", doc_endpoint_response, name="Latest", tags=["Redirects"],
                                      description="Requests made to endpoint `/latest/*`) will be "
                                                  "redirected to latest version, which is %s (i.e. `/%s/*`)" % (
                                                      semver, semver)))

    # define custom openapi for parent app, so that it only includes information about different versions.
    def custom_openapi_for_parent_app():
        if parent_app.openapi_schema:
            return parent_app.openapi_schema
        openapi_schema = get_openapi(
            title=parent_app.title,
            version=parent_app.version,
            description=parent_app.description + "\n This page only includes an overview of available versions of this "
                                                 "API. Refer to the documentation of a specific version for the actual "
                                                 "documentation, e.g. `/v1.0/redoc`",
            routes=doc_endpoints,
            tags=remove_non_present_openapi_tags(openapi_tags, doc_endpoints)
        )
        parent_app.openapi_schema = openapi_schema
        return parent_app.openapi_schema

    parent_app.openapi = custom_openapi_for_parent_app

    return parent_app
