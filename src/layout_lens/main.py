from layout_lens.core.application import Application
from layout_lens.core.settings import Settings


def main():
    settings = Settings()
    app = Application(settings)
    app.run()


if __name__ == "__main__":
    main()
