"""PyInstaller entry point for the bundled Kaggle CLI executable."""

from kaggle.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
