class PrivateResponseMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        response["Content-Security-Policy"] = "default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'"
        if request.path.startswith("/my-service/"):
            response["Content-Security-Policy"] = response["Content-Security-Policy"].replace("script-src 'none'", "script-src 'self'; connect-src 'self'")
            response["Permissions-Policy"] = "geolocation=(self)"
        elif request.path == "/dispatcher/":
            response["Content-Security-Policy"] = response["Content-Security-Policy"].replace("script-src 'none'", "script-src 'self'")
            response["Permissions-Policy"] = "geolocation=()"
        else:
            response["Permissions-Policy"] = "geolocation=()"
        response["Referrer-Policy"] = "same-origin"
        if not request.path.startswith("/static/"):
            response["Cache-Control"] = "no-store, private"
        return response
