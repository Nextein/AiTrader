from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from app.core.logger import logger
from fastapi.staticfiles import StaticFiles
from app.agents.governor_agent import governor
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.models import AuditLogModel, EquityModel, OrderModel, Base
from app.core.event_bus import event_bus
from app.core.analysis import AnalysisManager
import pandas as pd
import numpy as np
import asyncio
import uvicorn
import time

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Application starting up... DB tables created.")
    yield
    # Shutdown logic
    logger.info("Application shutting down...")

app = FastAPI(title="ChartChampion AI - Multi-Agent Trading System", lifespan=lifespan)

# Ensure database tables are created
Base.metadata.create_all(bind=engine)

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
    return response

@app.get("/")
async def root():
    logger.debug("Health check endpoint called")
    return {"message": "ChartChampion AI API is running", "status": "active"}

@app.post("/start")
async def start_trading(background_tasks: BackgroundTasks):
    logger.info("Received request to START trading system")
    if governor.is_running:
        logger.warning("Attempted to start trading but it is already running")
        return {"message": "Trading is already running"}
    
    background_tasks.add_task(governor.start)
    logger.info("Governor agent start task added to background")
    return {"message": "Trading system start command issued"}

@app.post("/stop")
async def stop_trading():
    logger.info("Received request to STOP trading system")
    if not governor.is_running:
        logger.warning("Attempted to stop trading but it is not running")
        return {"message": "Trading is not running"}
    
    await governor.stop()
    logger.info("Governor agent stopped")
    return {"message": "Trading system stop command issued"}

@app.post("/emergency-stop")
async def emergency_stop():
    logger.critical("EMERGENCY STOP command received! Closing all positions.")
    await governor.emergency_stop()
    return {"message": "EMERGENCY STOP command issued. All positions closing."}

@app.get("/status")
async def get_status():
    return {
        "is_running": governor.is_running,
        "config": {
            "symbols": settings.TRADING_SYMBOLS,
            "timeframe": settings.TIMEFRAME,
            "sandbox": settings.BINGX_IS_SANDBOX,
            "demo_mode": settings.DEMO_MODE
        },
        "agents": [agent.get_status() for agent in governor.agents]
    }

@app.post("/agents/restart/{name}")
async def restart_agent(name: str):
    logger.info(f"Request to restart agent: {name}")
    for agent in governor.agents:
        if agent.name == name:
            await agent.stop()
            asyncio.create_task(agent.start())
            logger.info(f"Agent {name} restarted")
            return {"message": f"Agent {name} restarted"}
    logger.error(f"Agent {name} not found for restart")
    raise HTTPException(status_code=404, detail=f"Agent {name} not found")

@app.get("/agents/{name}/events")
async def get_agent_events(name: str, limit: int = 50):
    """Get recent events created by a specific agent (Task 1)"""
    events = event_bus.get_agent_events(name, limit)
    if not events:
        # Check if agent exists
        agent_exists = any(agent.name == name for agent in governor.agents)
        if not agent_exists:
            raise HTTPException(status_code=404, detail=f"Agent {name} not found")
    return {"agent_name": name, "events": events, "count": len(events)}

@app.post("/agents/{name}/activate")
async def activate_agent(name: str):
    """Activate a specific agent (Task 2)"""
    logger.info(f"Request to activate agent: {name}")
    for agent in governor.agents:
        if agent.name == name:
            if hasattr(agent, 'is_active'):
                agent.is_active = True
                logger.info(f"Agent {name} activated")
                return {"message": f"Agent {name} activated", "is_active": True}
            else:
                logger.warning(f"Agent {name} does not support activation control")
                return {"message": f"Agent {name} does not support activation control"}
    raise HTTPException(status_code=404, detail=f"Agent {name} not found")

@app.post("/agents/{name}/deactivate")
async def deactivate_agent(name: str):
    """Deactivate a specific agent (Task 2)"""
    logger.info(f"Request to deactivate agent: {name}")
    for agent in governor.agents:
        if agent.name == name:
            if hasattr(agent, 'is_active'):
                agent.is_active = False
                logger.info(f"Agent {name} deactivated")
                return {"message": f"Agent {name} deactivated", "is_active": False}
            else:
                logger.warning(f"Agent {name} does not support activation control")
                return {"message": f"Agent {name} does not support activation control"}
    raise HTTPException(status_code=404, detail=f"Agent {name} not found")

@app.get("/logs")
async def get_logs(limit: int = 50):
    with SessionLocal() as db:
        logs = db.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).limit(limit).all()
        return logs

@app.get("/equity")
async def get_equity(limit: int = 100):
    with SessionLocal() as db:
        history = db.query(EquityModel).order_by(EquityModel.timestamp.asc()).limit(limit).all()
        history = db.query(EquityModel).order_by(EquityModel.timestamp.asc()).limit(limit).all()
        return history

@app.get("/portfolio")
async def get_portfolio():
    """Get current open positions (Task 1)"""
    with SessionLocal() as db:
        # In our simple model, anything FILLED (and not CLOSED) is an open position
        # We check for orders with status FILLED and closed_at is NULL
        # But wait, OrderModel status logic needs consistency.
        # DemoEngine updates status to CLOSED. 
        # Live execution needs logic to update status too (currently missing).
        # For now, we rely on the status field.
        
        orders = db.query(OrderModel).filter(
            OrderModel.status == 'FILLED',
            OrderModel.closed_at.is_(None)
        ).all()
        return orders

@app.get("/trades")
async def get_trades(limit: int = 100):
    """Get trade history (Task 2)"""
    with SessionLocal() as db:
        # Fetch closed orders
        trades = db.query(OrderModel).filter(
            OrderModel.status == 'CLOSED'
        ).order_by(OrderModel.closed_at.desc()).limit(limit).all()
        return trades

@app.get("/analysis/symbols")
async def get_analysis_symbols():
    """Get list of symbols with analysis objects (Task 2)"""
    return await AnalysisManager.get_all_symbols()

@app.get("/analysis/{symbol:path}")
async def get_analysis_data(symbol: str):
    """Get full analysis object for a symbol (Task 2)"""
    analysis = await AnalysisManager.get_analysis(symbol)
    data = await analysis.get_data()
    
    # Pre-process data to make it JSON serializable (convert DataFrames)
    return serialize_analysis_data(data)

def serialize_analysis_data(obj):
    if isinstance(obj, pd.DataFrame):
        # Only take last 100 rows to keep response size manageable
        return obj.tail(100).replace({np.nan: None}).to_dict(orient='records')
    elif isinstance(obj, dict):
        return {k: serialize_analysis_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_analysis_data(v) for v in obj]
    elif hasattr(obj, 'item'): # numpy types
        return obj.item()
    return obj

if __name__ == "__main__":
    logger.info("Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
