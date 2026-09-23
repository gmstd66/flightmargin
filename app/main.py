import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.adapters.codex_stdio import (
    CodexAppServer,
)

from app.core.config import (
    load_config,
)

from app.core.metrics import (
    enrich_sample,
)

from app.core.quota import (
    normalize_rate_limits,
)

from app.storage.sqlite_store import (
    SQLiteQuotaStore,
)


config = load_config()

PACKAGE_ROOT = Path(
    __file__
).resolve().parent

TEMPLATES_DIR = (
    PACKAGE_ROOT
    / "templates"
)

STATIC_DIR = (
    PACKAGE_ROOT
    / "static"
)

DATABASE_PATH = config.database_path
SAMPLE_INTERVAL = config.sample_seconds


codex = CodexAppServer(
    executable=config.codex_bin
)

store = SQLiteQuotaStore(
    DATABASE_PATH
)

collector_task = None

collector_status = {
    "running": False,
    "last_success": None,
    "last_error": None,
}


def collect_sync():
    try:
        if (
            not codex.process
            or codex.process.poll()
            is not None
        ):
            codex.start()

        response = (
            codex.get_rate_limits()
        )

        normalized = (
            normalize_rate_limits(
                response
            )
        )

        sample = (
            store.insert_sample(
                normalized
            )
        )

        collector_status[
            "last_success"
        ] = int(time.time())

        collector_status[
            "last_error"
        ] = None

        return sample

    except Exception as exc:
        collector_status[
            "last_error"
        ] = str(exc)

        codex.stop()

        raise


async def collect():
    return await asyncio.to_thread(
        collect_sync
    )


async def collector_loop():
    collector_status[
        "running"
    ] = True

    try:
        while True:
            started = time.monotonic()

            try:
                sample = (
                    await collect()
                )

                five = sample.get(
                    "five_hour_used"
                )

                weekly = sample.get(
                    "weekly_used"
                )

                five_remaining = (
                    100 - five
                    if five is not None
                    else None
                )

                weekly_remaining = (
                    100 - weekly
                    if weekly is not None
                    else None
                )

                print(
                    "Quota sample: "
                    f"5h={five_remaining}% "
                    f"weekly={weekly_remaining}%",
                    flush=True,
                )

            except Exception as exc:
                print(
                    "Quota collection error: "
                    f"{exc}",
                    flush=True,
                )

            elapsed = (
                time.monotonic()
                - started
            )

            await asyncio.sleep(
                max(
                    1,
                    SAMPLE_INTERVAL
                    - elapsed,
                )
            )

    except asyncio.CancelledError:
        pass

    finally:
        collector_status[
            "running"
        ] = False


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    global collector_task

    store.initialize()

    try:
        await collect()

    except Exception as exc:
        print(
            "Initial quota collection failed: "
            f"{exc}",
            flush=True,
        )

    collector_task = (
        asyncio.create_task(
            collector_loop()
        )
    )

    yield

    if collector_task:
        collector_task.cancel()

        try:
            await collector_task

        except asyncio.CancelledError:
            pass

    codex.stop()


app = FastAPI(
    title="Codex Quota Monitor",
    version="0.2.0",
    lifespan=lifespan,
)


templates = Jinja2Templates(
    directory=str(
        TEMPLATES_DIR
    )
)


app.mount(
    "/static",

    StaticFiles(
        directory=str(
            STATIC_DIR
        )
    ),

    name="static",
)


@app.get(
    "/",
    response_class=HTMLResponse,
)
async def dashboard(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/api/quota")
async def quota():
    sample = (
        store.get_latest_sample()
    )

    if not sample:
        raise HTTPException(
            status_code=503,
            detail=(
                "No quota sample available"
            ),
        )

    result = enrich_sample(
        sample
    )

    result["collector"] = (
        collector_status
    )

    return result


@app.post("/api/refresh")
async def refresh():
    try:
        sample = await collect()

        return enrich_sample(
            sample
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@app.get("/api/history")
async def history(
    hours: int = 168,
):
    hours = max(
        1,
        min(
            hours,
            720,
        ),
    )

    samples = (
        store.get_history(
            hours
        )
    )

    return {
        "hours": hours,
        "samples": samples,
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "0.2.0",
        "collector": collector_status,
        "database": str(
            DATABASE_PATH
        ),
        "sample_interval_seconds":
            SAMPLE_INTERVAL,
    }
