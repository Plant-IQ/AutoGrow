from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import stage, health, light, harvest, history, pump, observations, context, targets
from db.sqlite import init_db
from mqtt.subscriber import start_subscriber
from routers import plants 



app = FastAPI(title="AutoGrow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stage.router, prefix="/stage", tags=["stage"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(light.router, prefix="/light", tags=["light"])
app.include_router(harvest.router, prefix="/harvest-eta", tags=["harvest"])
app.include_router(history.router, prefix="/history", tags=["history"])
app.include_router(pump.router, prefix="/pump-status", tags=["pump"])
app.include_router(observations.router, prefix="/observations", tags=["observations"])
app.include_router(context.router, prefix="/context", tags=["context"])
app.include_router(targets.router, prefix="/targets", tags=["targets"])
app.include_router(plants.router, prefix="/plants", tags=["plants"])
app.include_router(plants.alias_router, tags=["plants"])

@app.on_event("startup")
def startup():
    init_db()
    start_subscriber()
    plants.sync_plants_now()
    plants.start_pending_refresher()
