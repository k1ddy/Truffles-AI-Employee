import sys
import os
import yaml
from fastapi.openapi.utils import get_openapi

# Add the parent directory to sys.path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

def generate_openapi():
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    
    # Ensure the directory exists
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contracts", "console_api")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "openapi.v1.yaml")
    
    with open(output_file, "w") as f:
        yaml.dump(openapi_schema, f, sort_keys=False)
    
    print(f"OpenAPI specification generated at: {output_file}")

if __name__ == "__main__":
    generate_openapi()
