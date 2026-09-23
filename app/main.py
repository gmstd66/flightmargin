import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

from app.codex_client import CodexClient
from app.database import (
    initialize_database,
    insert_sample,
    get_latest_sample,
    get_history,
)
from app.metrics import enrich_sample


BASE_DIR = Path("/opt/codex-quota")

client = CodexClient()

collector_task = None
collector_status = {
    "running": False,
    "last_success": None,
    "last_error": None,
}


def identify_windows(limits):
    five_hour = None
    weekly = None

    for bucket in (
        limits.get("primary"),
        limits.get("secondary"),
    ):
        if not bucket:
            continue

        duration = bucket.get("windowDurationMins")

        if duration == 300:
            five_hour = bucket

        elif duration == 10080:
            weekly = bucket

    return five_hour, weekly


def normalize(raw):
    limits = raw["limits"]

    five_hour, weekly = identify_windows(limits)

    credits = limits.get("credits") or {}
    reset_credits = raw.get("reset_credits") or {}

    return {
        "five_hour_used":
            five_hour.get("usedPercent")
            if five_hour else None,

        "five_hour_reset_at":
            five_hour.get("resetsAt")
            if five_hour else None,

        "weekly_used":
            weekly.get("usedPercent")
            if weekly else None,

        "weekly_reset_at":
            weekly.get("resetsAt")
            if weekly else None,

        "plan_type":
            limits.get("planType"),

        "reset_credits_available":
            reset_credits.get("availableCount", 0),

        "credits_balance":
            credits.get("balance"),

        "spend_control_reached":
            limits.get("spendControlReached", False),

        "rate_limit_reached_type":
            limits.get("rateLimitReachedType"),
    }


def collect_sync():
    try:
        if not client.process or client.process.poll() is not None:
            client.start()

        raw = client.get_rate_limits()
        normalized = normalize(raw)

        sample = insert_sample(normalized)

        collector_status["last_success"] = int(time.time())
        collector_status["last_error"] = None

        return sample

    except Exception as exc:
        collector_status["last_error"] = str(exc)

        client.stop()

        raise


async def collect():
    return await asyncio.to_thread(collect_sync)


async def collector_loop():
    collector_status["running"] = True

    try:
        while True:
            started = time.monotonic()

            try:
                sample = await collect()

                print(
                    f"Quota sample: "
                    f"5h={100 - sample['five_hour_used']}% "
                    f"weekly={100 - sample['weekly_used']}%",
                    flush=True,
                )

            except Exception as exc:
                print(
                    f"Quota collection error: {exc}",
                    flush=True,
                )

            elapsed = time.monotonic() - started

            await asyncio.sleep(
                max(1, 60 - elapsed)
            )

    except asyncio.CancelledError:
        pass

    finally:
        collector_status["running"] = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global collector_task

    initialize_database()

    try:
        await collect()
    except Exception as exc:
        print(
            f"Initial quota collection failed: {exc}",
            flush=True,
        )

    collector_task = asyncio.create_task(
        collector_loop()
    )

    yield

    if collector_task:
        collector_task.cancel()

        try:
            await collector_task
        except asyncio.CancelledError:
            pass

    client.stop()


app = FastAPI(
    title="Codex Quota Monitor",
    lifespan=lifespan,
)


templates = Jinja2Templates(
    directory=str(BASE_DIR / "app/templates")
)

app.mount(
    "/static",
    StaticFiles(
        directory=str(BASE_DIR / "app/static")
    ),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/api/quota")
async def quota():
    sample = get_latest_sample()

    if not sample:
        raise HTTPException(
            status_code=503,
            detail="No quota sample available",
        )

    result = enrich_sample(sample)
    result["collector"] = collector_status

    return result


@app.post("/api/refresh")
async def refresh():
    try:
        sample = await collect()
        return enrich_sample(sample)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@app.get("/api/history")
async def history(hours: int = 168):
    hours = max(1, min(hours, 720))

    samples = get_history(hours)

    return {
        "hours": hours,
        "samples": samples,
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "collector": collector_status,
    }
