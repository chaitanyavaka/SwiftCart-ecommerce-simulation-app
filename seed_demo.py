"""Reset and seed the SwiftCart marketplace database."""

from ecommerce_demo import create_app
from ecommerce_demo.seed import seed_demo_data


def main() -> None:
    app = create_app({"AUTO_SEED": False})
    with app.app_context():
        seed_demo_data(app.extensions["demo_db"])
        print("SwiftCart marketplace data reset and seeded.")


if __name__ == "__main__":
    main()
