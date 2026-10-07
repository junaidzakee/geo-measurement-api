from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

router = APIRouter(include_in_schema=False)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

body { margin: 0; background: #f4f6fb; font-family: 'Inter', sans-serif; }
body::before {
  content: ''; display: block; height: 6px;
  background: linear-gradient(90deg, #6366f1, #10b981);
}

.swagger-ui, .swagger-ui .opblock-tag, .swagger-ui .info .title { font-family: 'Inter', sans-serif; }
.swagger-ui .wrapper { max-width: 960px; }

.swagger-ui .info { margin: 0; padding: 48px 0 24px; }
.swagger-ui .info .title { font-weight: 700; font-size: 2.2rem; color: #1e1b4b; }
.swagger-ui .info .title small.version-stamp { background: #6366f1; }
.swagger-ui .info p, .swagger-ui .info li { font-size: 15px; line-height: 1.6; color: #374151; }

.swagger-ui .opblock-tag { font-weight: 600; color: #1e1b4b; border-bottom: 1px solid #e5e7eb; }

.swagger-ui .opblock {
  border-radius: 12px; border-width: 1px; margin: 0 0 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.swagger-ui .opblock .opblock-summary-method { border-radius: 8px; font-weight: 600; min-width: 70px; }
.swagger-ui .opblock.opblock-post { border-color: #10b981; background: #f0fdf9; }
.swagger-ui .opblock.opblock-post .opblock-summary-method { background: #10b981; }
.swagger-ui .opblock.opblock-get { border-color: #6366f1; background: #f5f5ff; }
.swagger-ui .opblock.opblock-get .opblock-summary-method { background: #6366f1; }

.swagger-ui .btn { border-radius: 8px; font-weight: 600; }
.swagger-ui .btn.execute { background: #6366f1; border-color: #6366f1; }
.swagger-ui .btn.execute:hover { background: #4f46e5; }
.swagger-ui input[type=text] { border-radius: 8px; }
.swagger-ui .scheme-container { background: transparent; box-shadow: none; }
"""


@router.get("/docs")
def docs(request: Request):
    app = request.app
    page = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} | Docs",
        swagger_ui_parameters={
            "tryItOutEnabled": True,
            # "defaultModelsExpandDepth": -1,
            "displayRequestDuration": True,
        },
    )
    html = page.body.decode().replace("</head>", f"<style>{CSS}</style></head>")
    return HTMLResponse(html)