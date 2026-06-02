import argparse
import os

from ecommerce_demo import create_app


app = create_app()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the SwiftCart marketplace app.")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "5000")))
    parser.add_argument("--debug", action="store_true", default=os.getenv("FLASK_DEBUG") == "1")
    args = parser.parse_args()

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=False,
    )
