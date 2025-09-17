from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import logging
import json
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour serveur
import matplotlib.pyplot as plt
import pandas as pd
import requests
import base64
import io
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration du logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "hybrid_system.log")

# Configuration du logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()  # Affichage dans la console aussi
    ]
)

logger = logging.getLogger("HybridSystemAPI")

# Configuration de la base de donnÃ©es PostgreSQL depuis les variables d'environnement
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Log de la configuration au dÃ©marrage
logger.info(f"DÃ©marrage de l'API SystÃ¨me Hybride")
logger.info(f"Configuration BDD - Host: {DB_HOST}, Port: {DB_PORT}, DB: {DB_NAME}, User: {DB_USER}")
logger.info(f"Niveau de log: {LOG_LEVEL}, Fichier de log: {LOG_FILE}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Test de connexion Ã  la base de donnÃ©es
try:
    # Test simple de connexion
    with engine.connect() as conn:
        logger.info("Connexion Ã  la base de donnÃ©es rÃ©ussie")
except Exception as e:
    logger.error(f"Erreur de connexion Ã  la base de donnÃ©es: {str(e)}")
    raise

# ModÃ¨le de base de donnÃ©es
class SensorData(Base):
    __tablename__ = "sensor_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    device_timestamp = Column(Integer)  # timestamp de l'ESP32
    
    # DonnÃ©es de tension et courant
    U1 = Column(Float)
    I1 = Column(Float)
    P1 = Column(Float)
    U2 = Column(Float)
    I2 = Column(Float)
    P2 = Column(Float)
    
    # DonnÃ©es des lampes
    currentLamp1 = Column(Float)
    currentLamp2 = Column(Float)
    powerLamp1 = Column(Float)
    powerLamp2 = Column(Float)
    
    # DonnÃ©es d'Ã©nergie
    savedEnergyS1 = Column(Float)
    savedEnergyS2 = Column(Float)
    savedEnergyT = Column(Float)
    
    # Ã‰tats
    etatS1 = Column(String)
    etatS2 = Column(String)
    etatLamp1 = Column(String)
    etatLamp2 = Column(String)
    sourceActive = Column(String)
    chargeActive = Column(String)
    

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    device_type = Column(String(20), nullable=False)  # 'lampe', 'prise', 'clim', 'brasseur'
    priority = Column(String(20), nullable=False)  # 'prioritaire', 'semi_prioritaire', 'non_prioritaire'
    current_state = Column(String(10), default='OFF')  # 'ON', 'OFF'
    power_consumption = Column(Float, default=0.0)  # Puissance en watts
    is_active = Column(Boolean, default=True)  # Pour dÃ©sactiver sans supprimer
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ForecastData(Base):
    __tablename__ = "forecast_data"
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    forecast_date = Column(DateTime, nullable=False)
    image_data = Column(String)  # Base64 encoded image
    raw_data = Column(String)  # JSON des données brutes
    title = Column(String(255))
    
class ForecastResponse(BaseModel):
    id: int
    created_at: datetime
    forecast_date: datetime
    title: str
    image_data: str
    
    class Config:
        from_attributes = True

# CrÃ©er les tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Tables de base de donnÃ©es crÃ©Ã©es/vÃ©rifiÃ©es avec succÃ¨s")
except Exception as e:
    logger.error(f"Erreur lors de la crÃ©ation des tables: {str(e)}")
    raise

# ModÃ¨les Pydantic pour la validation des donnÃ©es
class SensorReading(BaseModel):
    timestamp: int
    U1: float
    I1: float
    P1: float
    U2: float
    I2: float
    P2: float
    currentLamp1: float
    currentLamp2: float
    powerLamp1: float
    powerLamp2: float
    savedEnergyS1: float
    savedEnergyS2: float
    savedEnergyT: float
    etatS1: str
    etatS2: str
    etatLamp1: str
    etatLamp2: str
    sourceActive: str
    chargeActive: str

class SensorReadingResponse(BaseModel):
    id: int
    timestamp: datetime
    device_timestamp: int
    U1: float
    I1: float
    P1: float
    U2: float
    I2: float
    P2: float
    currentLamp1: float
    currentLamp2: float
    powerLamp1: float
    powerLamp2: float
    savedEnergyS1: float
    savedEnergyS2: float
    savedEnergyT: float
    etatS1: str
    etatS2: str
    etatLamp1: str
    etatLamp2: str
    sourceActive: str
    chargeActive: str

    class Config:
        from_attributes = True
    

class DeviceCreate(BaseModel):
    name: str
    device_type: str  # 'lampe', 'prise', 'clim', 'brasseur'
    priority: str  # 'prioritaire', 'semi_prioritaire', 'non_prioritaire'

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    device_type: Optional[str] = None
    priority: Optional[str] = None
    current_state: Optional[str] = None
    power_consumption: Optional[float] = None
    is_active: Optional[bool] = None

class DeviceResponse(BaseModel):
    id: int
    name: str
    device_type: str
    priority: str
    current_state: str
    power_consumption: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
  
class LampControl(BaseModel):
    lamp_id: int  
    action: str  

class LampControlResponse(BaseModel):
    status: str
    message: str
    lamp_id: int
    new_state: str

# Application FastAPI
app = FastAPI(title="SystÃ¨me de Gestion Hybride API", version="1.0.0")

# Configuration Solcast depuis les variables d'environnement
SOLCAST_API_KEY = os.getenv("SOLCAST_API_KEY")
SOLCAST_SITE_ID = os.getenv("SOLCAST_SITE_ID")
SOLCAST_BASE_URL = os.getenv("SOLCAST_BASE_URL")

if not all([SOLCAST_API_KEY, SOLCAST_SITE_ID, SOLCAST_BASE_URL]):
    logger.warning("Configuration Solcast incomplète - fonctionnalité prévision désactivée")

# Monter le dossier static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

logger.info("Application FastAPI initialisÃ©e")

# DÃ©pendance pour obtenir la session de base de donnÃ©es
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Erreur lors de l'accÃ¨s Ã  la base de donnÃ©es: {str(e)}")
        raise
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("indexa.html", {"request": request})

# Endpoints
@app.post("/data", response_model=dict)
async def receive_sensor_data(data: SensorReading, db: Session = Depends(get_db)):
    """
    Recevoir et stocker les donnÃ©es des capteurs de l'ESP32
    """
    # Log des donnÃ©es reÃ§ues
    logger.info("=== DONNÃ‰ES REÃ‡UES ===")
    logger.info(f"Timestamp ESP32: {data.timestamp}")
    logger.info(f"Source 1 - U1: {data.U1}V, I1: {data.I1}A, P1: {data.P1}W, Ã‰tat: {data.etatS1}")
    logger.info(f"Source 2 - U2: {data.U2}V, I2: {data.I2}A, P2: {data.P2}W, Ã‰tat: {data.etatS2}")
    logger.info(f"Lampe 1 - Courant: {data.currentLamp1}A, Puissance: {data.powerLamp1}W, Ã‰tat: {data.etatLamp1}")
    logger.info(f"Lampe 2 - Courant: {data.currentLamp2}A, Puissance: {data.powerLamp2}W, Ã‰tat: {data.etatLamp2}")
    logger.info(f"Ã‰nergie sauvÃ©e - S1: {data.savedEnergyS1}kWh, S2: {data.savedEnergyS2}kWh, Total: {data.savedEnergyT}kWh")
    logger.info(f"Source active: {data.sourceActive}, Charge active: {data.chargeActive}")
    
    try:
        db_reading = SensorData(
            device_timestamp=data.timestamp,
            U1=data.U1,
            I1=data.I1,
            P1=data.P1,
            U2=data.U2,
            I2=data.I2,
            P2=data.P2,
            currentLamp1=data.currentLamp1,
            currentLamp2=data.currentLamp2,
            powerLamp1=data.powerLamp1,
            powerLamp2=data.powerLamp2,
            savedEnergyS1=data.savedEnergyS1,
            savedEnergyS2=data.savedEnergyS2,
            savedEnergyT=data.savedEnergyT,
            etatS1=data.etatS1,
            etatS2=data.etatS2,
            etatLamp1=data.etatLamp1,
            etatLamp2=data.etatLamp2,
            sourceActive=data.sourceActive,
            chargeActive=data.chargeActive
        )
        
        db.add(db_reading)
        db.commit()
        db.refresh(db_reading)
        
        logger.info(f"DonnÃ©es enregistrÃ©es avec succÃ¨s - ID: {db_reading.id}, Timestamp DB: {db_reading.timestamp}")
        
        return {"status": "success", "id": db_reading.id, "message": "DonnÃ©es reÃ§ues et enregistrÃ©es"}
    
    except Exception as e:
        db.rollback()
        logger.error(f"ERREUR lors de l'enregistrement des donnÃ©es: {str(e)}")
        logger.error(f"DonnÃ©es qui ont causÃ© l'erreur: {json.dumps(data.dict(), indent=2, default=str)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'enregistrement: {str(e)}")

@app.get("/data/latest", response_model=SensorReadingResponse)
async def get_latest_data(db: Session = Depends(get_db)):
    """
    RÃ©cupÃ©rer les derniÃ¨res donnÃ©es enregistrÃ©es
    """
    try:
        logger.info("RequÃªte pour rÃ©cupÃ©rer les derniÃ¨res donnÃ©es")
        latest_reading = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
        
        if not latest_reading:
            logger.warning("Aucune donnÃ©e trouvÃ©e dans la base")
            raise HTTPException(status_code=404, detail="Aucune donnÃ©e trouvÃ©e")
        
        logger.info(f"DerniÃ¨res donnÃ©es rÃ©cupÃ©rÃ©es - ID: {latest_reading.id}, Timestamp: {latest_reading.timestamp}")
        return latest_reading
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la rÃ©cupÃ©ration des derniÃ¨res donnÃ©es: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.get("/data/history", response_model=List[SensorReadingResponse])
async def get_data_history(
    limit: int = 100,
    offset: int = 0,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    RÃ©cupÃ©rer l'historique des donnÃ©es avec pagination et filtres de date
    """
    try:
        logger.info(f"RequÃªte historique - Limit: {limit}, Offset: {offset}, Start: {start_date}, End: {end_date}")
        
        query = db.query(SensorData)
        
        if start_date:
            query = query.filter(SensorData.timestamp >= start_date)
            logger.info(f"Filtre appliquÃ© - Date dÃ©but: {start_date}")
        
        if end_date:
            query = query.filter(SensorData.timestamp <= end_date)
            logger.info(f"Filtre appliquÃ© - Date fin: {end_date}")
        
        readings = query.order_by(SensorData.timestamp.desc()).offset(offset).limit(limit).all()
        
        logger.info(f"Historique rÃ©cupÃ©rÃ© - {len(readings)} enregistrements")
        return readings
        
    except Exception as e:
        logger.error(f"Erreur lors de la rÃ©cupÃ©ration de l'historique: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.get("/data/stats", response_model=dict)
async def get_system_stats(db: Session = Depends(get_db)):
    """
    RÃ©cupÃ©rer les statistiques du systÃ¨me
    """
    try:
        logger.info("Calcul des statistiques du systÃ¨me")
        
        # DerniÃ¨re lecture
        latest = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
        
        if not latest:
            logger.warning("Aucune donnÃ©e disponible pour les statistiques")
            return {"error": "Aucune donnÃ©e disponible"}
        
        # Statistiques de base
        total_readings = db.query(SensorData).count()
        
        # Ã‰nergie totale consommÃ©e
        total_energy_s1 = latest.savedEnergyS1 if latest.savedEnergyS1 else 0
        total_energy_s2 = latest.savedEnergyS2 if latest.savedEnergyS2 else 0
        total_energy = latest.savedEnergyT if latest.savedEnergyT else 0
        
        # Puissance actuelle
        current_power_s1 = latest.P1 if latest.P1 else 0
        current_power_s2 = latest.P2 if latest.P2 else 0
        current_power_total = current_power_s1 + current_power_s2
        
        # Ã‰tat actuel du systÃ¨me
        system_status = {
            "source_1_active": latest.etatS1 == "ON",
            "source_2_active": latest.etatS2 == "ON",
            "lamp_1_active": latest.etatLamp1 == "ON",
            "lamp_2_active": latest.etatLamp2 == "ON",
            "active_source": latest.sourceActive,
            "active_charge": latest.chargeActive
        }
        
        stats = {
            "total_readings": total_readings,
            "energy_consumption": {
                "source_1_kwh": total_energy_s1,
                "source_2_kwh": total_energy_s2,
                "total_kwh": total_energy
            },
            "current_power": {
                "source_1_watts": current_power_s1,
                "source_2_watts": current_power_s2,
                "total_watts": current_power_total
            },
            "system_status": system_status,
            "last_update": latest.timestamp
        }
        
        logger.info(f"Statistiques calculÃ©es - Total lectures: {total_readings}, Puissance totale: {current_power_total}W")
        return stats
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul des statistiques: {str(e)}")

@app.get("/data/energy-report", response_model=dict)
async def get_energy_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    GÃ©nÃ©rer un rapport d'Ã©nergie pour une pÃ©riode donnÃ©e
    """
    try:
        logger.info(f"GÃ©nÃ©ration du rapport d'Ã©nergie - PÃ©riode: {start_date} Ã  {end_date}")
        
        query = db.query(SensorData)
        
        if start_date:
            query = query.filter(SensorData.timestamp >= start_date)
        
        if end_date:
            query = query.filter(SensorData.timestamp <= end_date)
        
        readings = query.order_by(SensorData.timestamp.asc()).all()
        
        if not readings:
            logger.warning("Aucune donnÃ©e trouvÃ©e pour la pÃ©riode spÃ©cifiÃ©e")
            return {"error": "Aucune donnÃ©e pour la pÃ©riode spÃ©cifiÃ©e"}
        
        # Calcul de la consommation pour la pÃ©riode
        first_reading = readings[0]
        last_reading = readings[-1]
        
        energy_consumed_s1 = last_reading.savedEnergyS1 - first_reading.savedEnergyS1
        energy_consumed_s2 = last_reading.savedEnergyS2 - first_reading.savedEnergyS2
        total_energy_consumed = energy_consumed_s1 + energy_consumed_s2
        
        # Calcul des moyennes
        avg_power_s1 = sum(r.P1 for r in readings if r.P1) / len([r for r in readings if r.P1])
        avg_power_s2 = sum(r.P2 for r in readings if r.P2) / len([r for r in readings if r.P2])
        
        # Temps d'utilisation des sources
        s1_active_count = len([r for r in readings if r.etatS1 == "ON"])
        s2_active_count = len([r for r in readings if r.etatS2 == "ON"])
        
        s1_usage_percentage = (s1_active_count / len(readings)) * 100 if readings else 0
        s2_usage_percentage = (s2_active_count / len(readings)) * 100 if readings else 0
        
        report = {
            "period": {
                "start": first_reading.timestamp,
                "end": last_reading.timestamp,
                "duration_hours": (last_reading.timestamp - first_reading.timestamp).total_seconds() / 3600
            },
            "energy_consumption": {
                "source_1_kwh": round(energy_consumed_s1, 3),
                "source_2_kwh": round(energy_consumed_s2, 3),
                "total_kwh": round(total_energy_consumed, 3)
            },
            "average_power": {
                "source_1_watts": round(avg_power_s1, 2),
                "source_2_watts": round(avg_power_s2, 2)
            },
            "usage_statistics": {
                "source_1_usage_percentage": round(s1_usage_percentage, 2),
                "source_2_usage_percentage": round(s2_usage_percentage, 2),
                "total_readings": len(readings)
            }
        }
        
        logger.info(f"Rapport gÃ©nÃ©rÃ© - {len(readings)} lectures, Ã‰nergie totale: {total_energy_consumed:.3f}kWh")
        return report
        
    except Exception as e:
        logger.error(f"Erreur lors de la gÃ©nÃ©ration du rapport: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la gÃ©nÃ©ration du rapport: {str(e)}")

@app.delete("/data/cleanup")
async def cleanup_old_data(days_to_keep: int = 30, db: Session = Depends(get_db)):
    """
    Nettoyer les anciennes donnÃ©es (garder seulement les X derniers jours)
    """
    try:
        logger.info(f"DÃ©marrage du nettoyage - Conservation de {days_to_keep} jours")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Compter les enregistrements Ã  supprimer
        count_to_delete = db.query(SensorData).filter(SensorData.timestamp < cutoff_date).count()
        
        deleted_count = db.query(SensorData).filter(
            SensorData.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Nettoyage terminÃ© - {deleted_count} enregistrements supprimÃ©s (date limite: {cutoff_date})")
        
        return {
            "status": "success",
            "deleted_records": deleted_count,
            "cutoff_date": cutoff_date,
            "message": f"DonnÃ©es antÃ©rieures Ã  {days_to_keep} jours supprimÃ©es"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors du nettoyage des donnÃ©es: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du nettoyage: {str(e)}")

@app.get("/")
async def root():
    """
    Point d'entrÃ©e de l'API
    """
    logger.info("AccÃ¨s Ã  l'endpoint racine de l'API")
    
    return {
        "message": "API du SystÃ¨me de Gestion Hybride",
        "version": "1.0.0",
        "database_config": {
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME,
            "user": DB_USER
        },
        "logging": {
            "level": LOG_LEVEL,
            "file": LOG_FILE
        },
        "endpoints": {
            "POST /data": "Recevoir donnÃ©es des capteurs",
            "GET /data/latest": "DerniÃ¨res donnÃ©es",
            "GET /data/history": "Historique des donnÃ©es",
            "GET /data/stats": "Statistiques du systÃ¨me",
            "GET /data/energy-report": "Rapport d'Ã©nergie",
            "DELETE /data/cleanup": "Nettoyer anciennes donnÃ©es",
            "GET /logs": "Consulter les logs rÃ©cents"
        }
    }

# Ajout d'un endpoint pour consulter les logs rÃ©cents
@app.get("/logs")
async def get_recent_logs(lines: int = 50):
    """
    RÃ©cupÃ©rer les derniÃ¨res lignes du fichier de log
    """
    try:
        logger.info(f"Demande de consultation des logs - {lines} derniÃ¨res lignes")
        
        if not os.path.exists(LOG_FILE):
            logger.warning(f"Fichier de log {LOG_FILE} non trouvÃ©")
            return {"error": "Fichier de log non trouvÃ©"}
        
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return {
            "log_file": LOG_FILE,
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines),
            "logs": [line.strip() for line in recent_lines]
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la lecture des logs: {str(e)}")
        return {"error": f"Erreur lors de la lecture des logs: {str(e)}"}
    
@app.post("/control/lamp", response_model=LampControlResponse)
async def control_lamp(control: LampControl, db: Session = Depends(get_db)):
    """
    ContrÃ´ler l'Ã©tat d'une lampe Ã  distance
    """
    try:
        global pending_commands
        
        logger.info(f"Commande reÃ§ue - Lampe {control.lamp_id}: {control.action}")
        
        # Validation des paramÃ¨tres
        if control.lamp_id not in [1, 2]:
            raise HTTPException(status_code=400, detail="lamp_id doit Ãªtre 1 ou 2")
        
        if control.action not in ["ON", "OFF"]:
            raise HTTPException(status_code=400, detail="action doit Ãªtre 'ON' ou 'OFF'")
        
        # Stocker la commande pour que l'ESP32 la rÃ©cupÃ¨re
        pending_commands[f"lamp{control.lamp_id}"] = control.action
        
        logger.info(f"Commande stockÃ©e - Lampe {control.lamp_id} -> {control.action}")
        
        return LampControlResponse(
            status="success",
            message=f"Commande envoyÃ©e pour Lampe {control.lamp_id}",
            lamp_id=control.lamp_id,
            new_state=control.action
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du contrÃ´le de la lampe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Variable globale pour stocker les commandes en attente
pending_commands = {}

@app.get("/control/get-commands")
async def get_pending_commands():
    """
    Endpoint pour que l'ESP32 rÃ©cupÃ¨re les commandes en attente
    """
    global pending_commands
    commands = pending_commands.copy()
    pending_commands.clear()  # Vider aprÃ¨s rÃ©cupÃ©ration
    logger.info(f"Commandes rÃ©cupÃ©rÃ©es par ESP32: {commands}")
    return {"commands": commands}

@app.get("/data/daily-energy", response_model=dict)
async def get_daily_energy(
    date: str,
    db: Session = Depends(get_db)
):
    """
    RÃ©cupÃ©rer la consommation d'Ã©nergie journaliÃ¨re par appareil pour une date donnÃ©e
    """
    try:
        logger.info(f"GÃ©nÃ©ration du rapport d'Ã©nergie journaliÃ¨re pour: {date}")
        
        # Convertir la date en datetime pour dÃ©but et fin de journÃ©e
        start_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = start_date.replace(hour=23, minute=59, second=59)
        
        # RÃ©cupÃ©rer toutes les donnÃ©es de la journÃ©e
        readings = db.query(SensorData).filter(
            SensorData.timestamp >= start_date,
            SensorData.timestamp <= end_date
        ).order_by(SensorData.timestamp.asc()).all()
        
        if not readings:
            logger.warning(f"Aucune donnÃ©e trouvÃ©e pour le {date}")
            return {
                "error": f"Aucune donnÃ©e trouvÃ©e pour le {date}",
                "date": date,
                "lamp1_energy": 0,
                "lamp2_energy": 0,
                "source1_energy": 0,
                "source2_energy": 0,
                "total_energy": 0
            }
        
        # Calcul de l'Ã©nergie consommÃ©e par chaque appareil
        first_reading = readings[0]
        last_reading = readings[-1]
        
        # Ã‰nergie des sources (diffÃ©rence entre fin et dÃ©but de journÃ©e)
        source1_energy = max(0, (last_reading.savedEnergyS1 or 0) - (first_reading.savedEnergyS1 or 0))
        source2_energy = max(0, (last_reading.savedEnergyS2 or 0) - (first_reading.savedEnergyS2 or 0))
        
        # Estimation de l'Ã©nergie des lampes basÃ©e sur la puissance moyenne et le temps d'utilisation
        lamp1_total_power = 0
        lamp2_total_power = 0
        lamp1_on_duration = 0
        lamp2_on_duration = 0
        
        # Calcul basÃ© sur les lectures avec un intervalle estimÃ© entre chaque lecture
        interval_hours = 0.05  # Supposons 3 minutes entre chaque lecture (3/60 = 0.05h)
        
        for reading in readings:
            if reading.etatLamp1 == 'ON' and reading.powerLamp1:
                lamp1_total_power += reading.powerLamp1 * interval_hours
                lamp1_on_duration += interval_hours
                
            if reading.etatLamp2 == 'ON' and reading.powerLamp2:
                lamp2_total_power += reading.powerLamp2 * interval_hours
                lamp2_on_duration += interval_hours
        
        # Convertir en kWh
        lamp1_energy = lamp1_total_power / 1000  # Watts to kWh
        lamp2_energy = lamp2_total_power / 1000  # Watts to kWh
        
        total_energy = source1_energy + source2_energy
        
        result = {
            "date": date,
            "lamp1_energy": round(lamp1_energy, 3),
            "lamp2_energy": round(lamp2_energy, 3),
            "source1_energy": round(source1_energy, 3),
            "source2_energy": round(source2_energy, 3),
            "total_energy": round(total_energy, 3),
            "statistics": {
                "total_readings": len(readings),
                "lamp1_on_duration_hours": round(lamp1_on_duration, 2),
                "lamp2_on_duration_hours": round(lamp2_on_duration, 2),
                "period_start": first_reading.timestamp,
                "period_end": last_reading.timestamp
            }
        }
        
        logger.info(f"Ã‰nergie journaliÃ¨re calculÃ©e - L1: {lamp1_energy:.3f}kWh, L2: {lamp2_energy:.3f}kWh, S1: {source1_energy:.3f}kWh, S2: {source2_energy:.3f}kWh")
        return result
        
    except ValueError as e:
        logger.error(f"Format de date invalide: {date}")
        raise HTTPException(status_code=400, detail=f"Format de date invalide. Utilisez YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Erreur lors du calcul de l'Ã©nergie journaliÃ¨re: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul de l'Ã©nergie journaliÃ¨re: {str(e)}")

@app.get("/devices", response_model=List[DeviceResponse])
async def get_all_devices(db: Session = Depends(get_db)):
    """RÃ©cupÃ©rer tous les appareils"""
    try:
        devices = db.query(Device).filter(Device.is_active == True).order_by(Device.priority, Device.name).all()
        return devices
    except Exception as e:
        logger.error(f"Erreur lors de la rÃ©cupÃ©ration des appareils: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.post("/devices", response_model=DeviceResponse)
async def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    """CrÃ©er un nouvel appareil"""
    try:
        # Validation des types et prioritÃ©s
        valid_types = ['lampe', 'prise', 'clim', 'brasseur']
        valid_priorities = ['prioritaire', 'semi_prioritaire', 'non_prioritaire']
        
        if device.device_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Type d'appareil invalide. Utilisez: {valid_types}")
        
        if device.priority not in valid_priorities:
            raise HTTPException(status_code=400, detail=f"PrioritÃ© invalide. Utilisez: {valid_priorities}")
        
        db_device = Device(**device.dict())
        db.add(db_device)
        db.commit()
        db.refresh(db_device)
        
        logger.info(f"Nouvel appareil crÃ©Ã©: {device.name} ({device.device_type}) - PrioritÃ©: {device.priority}")
        return db_device
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de la crÃ©ation de l'appareil: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la crÃ©ation: {str(e)}")

@app.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(device_id: int, device: DeviceUpdate, db: Session = Depends(get_db)):
    """Mettre Ã  jour un appareil"""
    try:
        db_device = db.query(Device).filter(Device.id == device_id).first()
        if not db_device:
            raise HTTPException(status_code=404, detail="Appareil non trouvÃ©")
        
        # Validation si les champs sont fournis
        if device.device_type:
            valid_types = ['lampe', 'prise', 'clim', 'brasseur']
            if device.device_type not in valid_types:
                raise HTTPException(status_code=400, detail=f"Type d'appareil invalide. Utilisez: {valid_types}")
        
        if device.priority:
            valid_priorities = ['prioritaire', 'semi_prioritaire', 'non_prioritaire']
            if device.priority not in valid_priorities:
                raise HTTPException(status_code=400, detail=f"PrioritÃ© invalide. Utilisez: {valid_priorities}")
        
        # Mettre Ã  jour les champs fournis
        for key, value in device.dict(exclude_unset=True).items():
            setattr(db_device, key, value)
        
        db_device.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_device)
        
        logger.info(f"Appareil mis Ã  jour: ID {device_id}")
        return db_device
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de la mise Ã  jour de l'appareil: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise Ã  jour: {str(e)}")

@app.delete("/devices/{device_id}")
async def delete_device(device_id: int, db: Session = Depends(get_db)):
    """Supprimer (dÃ©sactiver) un appareil"""
    try:
        db_device = db.query(Device).filter(Device.id == device_id).first()
        if not db_device:
            raise HTTPException(status_code=404, detail="Appareil non trouvÃ©")
        
        db_device.is_active = False
        db_device.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Appareil dÃ©sactivÃ©: ID {device_id}")
        return {"message": f"Appareil {db_device.name} dÃ©sactivÃ© avec succÃ¨s"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de la suppression de l'appareil: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")

@app.post("/control/device", response_model=dict)
async def control_device(device_id: int, action: str, db: Session = Depends(get_db)):
    """ContrÃ´ler un appareil"""
    try:
        if action not in ["ON", "OFF"]:
            raise HTTPException(status_code=400, detail="action doit Ãªtre 'ON' ou 'OFF'")
        
        db_device = db.query(Device).filter(Device.id == device_id).first()
        if not db_device:
            raise HTTPException(status_code=404, detail="Appareil non trouvÃ©")
        
        # Stocker la commande pour l'ESP32
        global pending_commands
        pending_commands[f"device_{device_id}"] = action
        
        # Mettre Ã  jour l'Ã©tat dans la base de donnÃ©es
        db_device.current_state = action
        db_device.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Commande envoyÃ©e - Appareil {db_device.name} (ID: {device_id}): {action}")
        
        return {
            "status": "success",
            "message": f"Commande envoyÃ©e pour {db_device.name}",
            "device_id": device_id,
            "device_name": db_device.name,
            "new_state": action
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du contrÃ´le de l'appareil: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.post("/forecast/generate", response_model=dict)
async def generate_forecast(db: Session = Depends(get_db)):
    """
    Générer une nouvelle prévision solaire
    """
    try:
        if not all([SOLCAST_API_KEY, SOLCAST_SITE_ID, SOLCAST_BASE_URL]):
            raise HTTPException(status_code=503, detail="Configuration Solcast manquante")
        
        logger.info("Génération d'une nouvelle prévision solaire")
        
        # Appel à l'API Solcast
        url = f"{SOLCAST_BASE_URL}/{SOLCAST_SITE_ID}/forecasts?format=json"
        headers = {'Authorization': f'Bearer {SOLCAST_API_KEY}'}
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Erreur API Solcast: {response.status_code} - {response.text}")
            raise HTTPException(status_code=502, detail=f"Erreur API Solcast: {response.status_code}")
        
        data = response.json()
        
        # Traitement des données
        df_forecasts = pd.DataFrame(data['forecasts'])
        df_forecasts['period_end'] = pd.to_datetime(df_forecasts['period_end'])
        
        # Conversion en kW
        for col in ['pv_estimate', 'pv_estimate10', 'pv_estimate90']:
            df_forecasts[col] = df_forecasts[col] / 1000
        
        df_forecasts.rename(columns={
            'pv_estimate': 'forecast_median_kw',
            'pv_estimate10': 'forecast_pessimistic_kw',
            'pv_estimate90': 'forecast_optimistic_kw'
        }, inplace=True)
        
        # Génération du graphique
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Plage de confiance
        ax.fill_between(df_forecasts['period_end'],
                        df_forecasts['forecast_pessimistic_kw'],
                        df_forecasts['forecast_optimistic_kw'],
                        color='orange',
                        alpha=0.3,
                        label='Plage de Confiance à 80%')
        
        # Ligne médiane
        ax.plot(df_forecasts['period_end'],
                df_forecasts['forecast_median_kw'],
                color='red',
                linestyle='-',
                linewidth=2,
                label='Prédiction Médiane')
        
        # Formatage du graphique
        ax.set_title('Prévision de Production Solaire', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Date et Heure', fontsize=12)
        ax.set_ylabel('Puissance AC Prévue (kW)', fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend(fontsize=11)
        
        # Formatage des dates sur l'axe X
        ax.xaxis.set_major_formatter(DateFormatter('%d/%m %H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        
        plt.tight_layout()
        
        # Conversion de l'image en base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        
        # Sauvegarde en base de données
        now = datetime.utcnow()
        title = f"Prévision générée le {now.strftime('%d/%m/%Y')} à {now.strftime('%H:%M')}"
        
        forecast_record = ForecastData(
            forecast_date=now,
            image_data=image_base64,
            raw_data=json.dumps(data),
            title=title
        )
        
        db.add(forecast_record)
        db.commit()
        db.refresh(forecast_record)
        
        logger.info(f"Prévision générée et sauvegardée - ID: {forecast_record.id}")
        
        return {
            "status": "success",
            "message": "Prévision générée avec succès",
            "forecast_id": forecast_record.id,
            "title": title,
            "image_data": f"data:image/png;base64,{image_base64}",
            "data_points": len(df_forecasts)
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur de connexion Solcast: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Erreur de connexion à l'API Solcast: {str(e)}")
    except Exception as e:
        logger.error(f"Erreur lors de la génération de prévision: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération: {str(e)}")

@app.get("/forecast/history", response_model=List[ForecastResponse])
async def get_forecast_history(limit: int = 10, db: Session = Depends(get_db)):
    """
    Récupérer l'historique des prévisions
    """
    try:
        forecasts = db.query(ForecastData).order_by(ForecastData.created_at.desc()).limit(limit).all()
        
        # Convertir les données pour la réponse
        result = []
        for forecast in forecasts:
            result.append(ForecastResponse(
                id=forecast.id,
                created_at=forecast.created_at,
                forecast_date=forecast.forecast_date,
                title=forecast.title,
                image_data=f"data:image/png;base64,{forecast.image_data}"
            ))
        
        logger.info(f"Historique des prévisions récupéré - {len(result)} enregistrements")
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.delete("/forecast/{forecast_id}")
async def delete_forecast(forecast_id: int, db: Session = Depends(get_db)):
    """
    Supprimer une prévision
    """
    try:
        forecast = db.query(ForecastData).filter(ForecastData.id == forecast_id).first()
        if not forecast:
            raise HTTPException(status_code=404, detail="Prévision non trouvée")
        
        db.delete(forecast)
        db.commit()
        
        logger.info(f"Prévision supprimée - ID: {forecast_id}")
        return {"message": "Prévision supprimée avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.get("/prevision")
async def prevision_page(request: Request):
    return templates.TemplateResponse("prevision.html", {"request": request})

Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn
    logger.info("DÃ©marrage du serveur FastAPI...")
    uvicorn.run(app, host="0.0.0.0", port=8000)