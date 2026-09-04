import uvicorn
import os
import sys

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    print("\n" + "=" * 65)
    print("  SENTINEL -- AP FRAUD & DUPLICATE-PAYMENT CONTROL AGENT")
    print("=" * 65)
    print(f"Server running at: http://{host}:{port}")
    print(f"Web Dashboard UI: http://{host}:{port}/")
    print(f"API Documentation: http://{host}:{port}/docs")
    print("=" * 65 + "\n")
    uvicorn.run("backend.server:app", host=host, port=port, reload=True)
