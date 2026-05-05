"""
Entry-point for the Inventory Management application.
Usage:  python run.py
        python run.py --config path/to/secrets.ini
"""

import argparse
from app import create_app

def main():
    parser = argparse.ArgumentParser(description="Inventory Management System")
    parser.add_argument(
        "--config",
        default="config/secrets.ini",
        help="Path to the secrets / configuration INI file",
    )
    args = parser.parse_args()

    app = create_app(config_path=args.config)
    app.run(
        host=app.config.get("HOST", "0.0.0.0"),
        port=int(app.config.get("PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )

if __name__ == "__main__":
    main()