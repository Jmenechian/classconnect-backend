from fastapi import FastAPI


def api_setup():
    global _openapi
    _openapi = FastAPI.openapi

    def openapi(self: FastAPI):
        """
        Removes 422 from the api schema which is in all endpoints when using pydantic and does not follow the RFC 7807 standard
        Will still send it if it happens, just ignore it as an example value schema in the UI
        """

        _openapi(self)

        for path_item in self.openapi_schema.get("paths", {}).values():
            for operation in path_item.values():
                responses = operation.get("responses", {})
                if "422" in responses:
                    del responses["422"]

        return self.openapi_schema

    FastAPI.openapi = openapi
