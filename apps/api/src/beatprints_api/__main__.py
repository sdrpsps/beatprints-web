import uvicorn

from beatprints_api.config import settings


def main() -> None:
    uvicorn.run(
        "beatprints_api.main:app",
        host="0.0.0.0",
        port=settings.port,
        workers=settings.workers,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
