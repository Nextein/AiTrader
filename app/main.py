from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from app.agents.governor_agent import governor
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.models import AuditLogModel, EquityModel, Base
import uvicorn

app = FastAPI(title="ChartChampion AI - Multi-Agent Trading System")

# Ensure database tables are created
Base.metadata.create_all(bind=engine)

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def root():
    return {"message": "ChartChampion AI API is running", "status": "active"}

@app.post("/start")
async def start_trading(background_tasks: BackgroundTasks):
    if governor.is_running:
        return {"message": "Trading is already running"}
    
    background_tasks.add_task(governor.start)
    return {"message": "Trading system start command issued"}

@app.post("/stop")
async def stop_trading():
    if not governor.is_running:
        return {"message": "Trading is not running"}
    
    await governor.stop()
    return {"message": "Trading system stop command issued"}

@app.post("/emergency-stop")
async def emergency_stop():
    await governor.emergency_stop()
    return {"message": "EMERGENCY STOP command issued. All positions closing."}

@app.get("/status")
async def get_status():
    return {
        "is_running": governor.is_running,
        "config": {
            "symbols": settings.TRADING_SYMBOLS,
            "timeframe": settings.TIMEFRAME,
            "sandbox": settings.BINGX_IS_SANDBOX
        },
        "agents": [agent.get_status() for agent in governor.agents]
    }

@app.post("/agents/restart/{name}")
async def restart_agent(name: str):
    for agent in governor.agents:
        if agent.name == name:
            await agent.stop()
            asyncio.create_task(agent.start())
            return {"message": f"Agent {name} restarted"}
    return {"error": f"Agent {name} not found"}, 404

@app.get("/logs")
async def get_logs(limit: int = 50):
    with SessionLocal() as db:
        logs = db.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).limit(limit).all()
        return logs

@app.get("/equity")
async def get_equity(limit: int = 100):
    with SessionLocal() as db:
        history = db.query(EquityModel).order_by(EquityModel.timestamp.asc()).limit(limit).all()
        return history

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
