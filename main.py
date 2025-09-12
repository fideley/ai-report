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

# Configuration de la base de données PostgreSQL depuis les variables d'environnement
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Log de la configuration au démarrage
logger.info(f"Démarrage de l'API Système Hybride")
logger.info(f"Configuration BDD - Host: {DB_HOST}, Port: {DB_PORT}, DB: {DB_NAME}, User: {DB_USER}")
logger.info(f"Niveau de log: {LOG_LEVEL}, Fichier de log: {LOG_FILE}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Test de connexion à la base de données
try:
    # Test simple de connexion
    with engine.connect() as conn:
        logger.info("Connexion à la base de données réussie")
except Exception as e:
    logger.error(f"Erreur de connexion à la base de données: {str(e)}")
    raise

# Modèle de base de données
class SensorData(Base):
    __tablename__ = "sensor_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    device_timestamp = Column(Integer)  # timestamp de l'ESP32
    
    # Données de tension et courant
    U1 = Column(Float)
    I1 = Column(Float)
    P1 = Column(Float)
    U2 = Column(Float)
    I2 = Column(Float)
    P2 = Column(Float)
    
    # Données des lampes
    currentLamp1 = Column(Float)
    currentLamp2 = Column(Float)
    powerLamp1 = Column(Float)
    powerLamp2 = Column(Float)
    
    # Données d'énergie
    savedEnergyS1 = Column(Float)
    savedEnergyS2 = Column(Float)
    savedEnergyT = Column(Float)
    
    # États
    etatS1 = Column(String)
    etatS2 = Column(String)
    etatLamp1 = Column(String)
    etatLamp2 = Column(String)
    sourceActive = Column(String)
    chargeActive = Column(String)

# Créer les tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Tables de base de données créées/vérifiées avec succès")
except Exception as e:
    logger.error(f"Erreur lors de la création des tables: {str(e)}")
    raise

# Modèles Pydantic pour la validation des données
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
    
    
class LampControl(BaseModel):
    lamp_id: int  
    action: str  

class LampControlResponse(BaseModel):
    status: str
    message: str
    lamp_id: int
    new_state: str

# Application FastAPI
app = FastAPI(title="Système de Gestion Hybride API", version="1.0.0")


# Monter le dossier static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

logger.info("Application FastAPI initialisée")

# Dépendance pour obtenir la session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Erreur lors de l'accès à la base de données: {str(e)}")
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
    Recevoir et stocker les données des capteurs de l'ESP32
    """
    # Log des données reçues
    logger.info("=== DONNÉES REÇUES ===")
    logger.info(f"Timestamp ESP32: {data.timestamp}")
    logger.info(f"Source 1 - U1: {data.U1}V, I1: {data.I1}A, P1: {data.P1}W, État: {data.etatS1}")
    logger.info(f"Source 2 - U2: {data.U2}V, I2: {data.I2}A, P2: {data.P2}W, État: {data.etatS2}")
    logger.info(f"Lampe 1 - Courant: {data.currentLamp1}A, Puissance: {data.powerLamp1}W, État: {data.etatLamp1}")
    logger.info(f"Lampe 2 - Courant: {data.currentLamp2}A, Puissance: {data.powerLamp2}W, État: {data.etatLamp2}")
    logger.info(f"Énergie sauvée - S1: {data.savedEnergyS1}kWh, S2: {data.savedEnergyS2}kWh, Total: {data.savedEnergyT}kWh")
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
        
        logger.info(f"Données enregistrées avec succès - ID: {db_reading.id}, Timestamp DB: {db_reading.timestamp}")
        
        return {"status": "success", "id": db_reading.id, "message": "Données reçues et enregistrées"}
    
    except Exception as e:
        db.rollback()
        logger.error(f"ERREUR lors de l'enregistrement des données: {str(e)}")
        logger.error(f"Données qui ont causé l'erreur: {json.dumps(data.dict(), indent=2, default=str)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'enregistrement: {str(e)}")

@app.get("/data/latest", response_model=SensorReadingResponse)
async def get_latest_data(db: Session = Depends(get_db)):
    """
    Récupérer les dernières données enregistrées
    """
    try:
        logger.info("Requête pour récupérer les dernières données")
        latest_reading = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
        
        if not latest_reading:
            logger.warning("Aucune donnée trouvée dans la base")
            raise HTTPException(status_code=404, detail="Aucune donnée trouvée")
        
        logger.info(f"Dernières données récupérées - ID: {latest_reading.id}, Timestamp: {latest_reading.timestamp}")
        return latest_reading
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des dernières données: {str(e)}")
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
    Récupérer l'historique des données avec pagination et filtres de date
    """
    try:
        logger.info(f"Requête historique - Limit: {limit}, Offset: {offset}, Start: {start_date}, End: {end_date}")
        
        query = db.query(SensorData)
        
        if start_date:
            query = query.filter(SensorData.timestamp >= start_date)
            logger.info(f"Filtre appliqué - Date début: {start_date}")
        
        if end_date:
            query = query.filter(SensorData.timestamp <= end_date)
            logger.info(f"Filtre appliqué - Date fin: {end_date}")
        
        readings = query.order_by(SensorData.timestamp.desc()).offset(offset).limit(limit).all()
        
        logger.info(f"Historique récupéré - {len(readings)} enregistrements")
        return readings
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.get("/data/stats", response_model=dict)
async def get_system_stats(db: Session = Depends(get_db)):
    """
    Récupérer les statistiques du système
    """
    try:
        logger.info("Calcul des statistiques du système")
        
        # Dernière lecture
        latest = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
        
        if not latest:
            logger.warning("Aucune donnée disponible pour les statistiques")
            return {"error": "Aucune donnée disponible"}
        
        # Statistiques de base
        total_readings = db.query(SensorData).count()
        
        # Énergie totale consommée
        total_energy_s1 = latest.savedEnergyS1 if latest.savedEnergyS1 else 0
        total_energy_s2 = latest.savedEnergyS2 if latest.savedEnergyS2 else 0
        total_energy = latest.savedEnergyT if latest.savedEnergyT else 0
        
        # Puissance actuelle
        current_power_s1 = latest.P1 if latest.P1 else 0
        current_power_s2 = latest.P2 if latest.P2 else 0
        current_power_total = current_power_s1 + current_power_s2
        
        # État actuel du système
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
        
        logger.info(f"Statistiques calculées - Total lectures: {total_readings}, Puissance totale: {current_power_total}W")
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
    Générer un rapport d'énergie pour une période donnée
    """
    try:
        logger.info(f"Génération du rapport d'énergie - Période: {start_date} à {end_date}")
        
        query = db.query(SensorData)
        
        if start_date:
            query = query.filter(SensorData.timestamp >= start_date)
        
        if end_date:
            query = query.filter(SensorData.timestamp <= end_date)
        
        readings = query.order_by(SensorData.timestamp.asc()).all()
        
        if not readings:
            logger.warning("Aucune donnée trouvée pour la période spécifiée")
            return {"error": "Aucune donnée pour la période spécifiée"}
        
        # Calcul de la consommation pour la période
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
        
        logger.info(f"Rapport généré - {len(readings)} lectures, Énergie totale: {total_energy_consumed:.3f}kWh")
        return report
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la génération du rapport: {str(e)}")

@app.delete("/data/cleanup")
async def cleanup_old_data(days_to_keep: int = 30, db: Session = Depends(get_db)):
    """
    Nettoyer les anciennes données (garder seulement les X derniers jours)
    """
    try:
        logger.info(f"Démarrage du nettoyage - Conservation de {days_to_keep} jours")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Compter les enregistrements à supprimer
        count_to_delete = db.query(SensorData).filter(SensorData.timestamp < cutoff_date).count()
        
        deleted_count = db.query(SensorData).filter(
            SensorData.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Nettoyage terminé - {deleted_count} enregistrements supprimés (date limite: {cutoff_date})")
        
        return {
            "status": "success",
            "deleted_records": deleted_count,
            "cutoff_date": cutoff_date,
            "message": f"Données antérieures à {days_to_keep} jours supprimées"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors du nettoyage des données: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du nettoyage: {str(e)}")

@app.get("/")
async def root():
    """
    Point d'entrée de l'API
    """
    logger.info("Accès à l'endpoint racine de l'API")
    
    return {
        "message": "API du Système de Gestion Hybride",
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
            "POST /data": "Recevoir données des capteurs",
            "GET /data/latest": "Dernières données",
            "GET /data/history": "Historique des données",
            "GET /data/stats": "Statistiques du système",
            "GET /data/energy-report": "Rapport d'énergie",
            "DELETE /data/cleanup": "Nettoyer anciennes données",
            "GET /logs": "Consulter les logs récents"
        }
    }

# Ajout d'un endpoint pour consulter les logs récents
@app.get("/logs")
async def get_recent_logs(lines: int = 50):
    """
    Récupérer les dernières lignes du fichier de log
    """
    try:
        logger.info(f"Demande de consultation des logs - {lines} dernières lignes")
        
        if not os.path.exists(LOG_FILE):
            logger.warning(f"Fichier de log {LOG_FILE} non trouvé")
            return {"error": "Fichier de log non trouvé"}
        
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
    Contrôler l'état d'une lampe à distance
    """
    try:
        global pending_commands
        
        logger.info(f"Commande reçue - Lampe {control.lamp_id}: {control.action}")
        
        # Validation des paramètres
        if control.lamp_id not in [1, 2]:
            raise HTTPException(status_code=400, detail="lamp_id doit être 1 ou 2")
        
        if control.action not in ["ON", "OFF"]:
            raise HTTPException(status_code=400, detail="action doit être 'ON' ou 'OFF'")
        
        # Stocker la commande pour que l'ESP32 la récupère
        pending_commands[f"lamp{control.lamp_id}"] = control.action
        
        logger.info(f"Commande stockée - Lampe {control.lamp_id} -> {control.action}")
        
        return LampControlResponse(
            status="success",
            message=f"Commande envoyée pour Lampe {control.lamp_id}",
            lamp_id=control.lamp_id,
            new_state=control.action
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du contrôle de la lampe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Variable globale pour stocker les commandes en attente
pending_commands = {}

@app.get("/control/get-commands")
async def get_pending_commands():
    """
    Endpoint pour que l'ESP32 récupère les commandes en attente
    """
    global pending_commands
    commands = pending_commands.copy()
    pending_commands.clear()  # Vider après récupération
    logger.info(f"Commandes récupérées par ESP32: {commands}")
    return {"commands": commands}

@app.get("/data/daily-energy", response_model=dict)
async def get_daily_energy(
    date: str,
    db: Session = Depends(get_db)
):
    """
    Récupérer la consommation d'énergie journalière par appareil pour une date donnée
    """
    try:
        logger.info(f"Génération du rapport d'énergie journalière pour: {date}")
        
        # Convertir la date en datetime pour début et fin de journée
        start_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = start_date.replace(hour=23, minute=59, second=59)
        
        # Récupérer toutes les données de la journée
        readings = db.query(SensorData).filter(
            SensorData.timestamp >= start_date,
            SensorData.timestamp <= end_date
        ).order_by(SensorData.timestamp.asc()).all()
        
        if not readings:
            logger.warning(f"Aucune donnée trouvée pour le {date}")
            return {
                "error": f"Aucune donnée trouvée pour le {date}",
                "date": date,
                "lamp1_energy": 0,
                "lamp2_energy": 0,
                "source1_energy": 0,
                "source2_energy": 0,
                "total_energy": 0
            }
        
        # Calcul de l'énergie consommée par chaque appareil
        first_reading = readings[0]
        last_reading = readings[-1]
        
        # Énergie des sources (différence entre fin et début de journée)
        source1_energy = max(0, (last_reading.savedEnergyS1 or 0) - (first_reading.savedEnergyS1 or 0))
        source2_energy = max(0, (last_reading.savedEnergyS2 or 0) - (first_reading.savedEnergyS2 or 0))
        
        # Estimation de l'énergie des lampes basée sur la puissance moyenne et le temps d'utilisation
        lamp1_total_power = 0
        lamp2_total_power = 0
        lamp1_on_duration = 0
        lamp2_on_duration = 0
        
        # Calcul basé sur les lectures avec un intervalle estimé entre chaque lecture
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
        
        logger.info(f"Énergie journalière calculée - L1: {lamp1_energy:.3f}kWh, L2: {lamp2_energy:.3f}kWh, S1: {source1_energy:.3f}kWh, S2: {source2_energy:.3f}kWh")
        return result
        
    except ValueError as e:
        logger.error(f"Format de date invalide: {date}")
        raise HTTPException(status_code=400, detail=f"Format de date invalide. Utilisez YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Erreur lors du calcul de l'énergie journalière: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul de l'énergie journalière: {str(e)}")

    
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn
    logger.info("Démarrage du serveur FastAPI...")
    uvicorn.run(app, host="0.0.0.0", port=8000)