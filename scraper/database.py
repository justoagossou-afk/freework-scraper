import os
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text
from dataclasses import asdict

load_dotenv()

# ── Connexion ──────────────────────────────────────────
DB_USER     = os.getenv("SCRAPER_DB_USER")
DB_PASSWORD = os.getenv("SCRAPER_DB_PASSWORD")
DB_NAME     = os.getenv("SCRAPER_DB_NAME")
DB_HOST     = os.getenv("SCRAPER_DB_HOST", "postgres")
DB_PORT     = os.getenv("SCRAPER_DB_PORT", "5432")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_engine():
    """Crée la connexion à PostgreSQL"""
    return create_engine(DATABASE_URL)


def create_table():
    """Crée la table jobs si elle n'existe pas"""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                title TEXT,
                description TEXT,
                location TEXT,
                candidate_profile TEXT,
                published_at TEXT,
                experience_level TEXT,
                min_daily TEXT,
                max_daily TEXT,
                min_annual_salary TEXT,
                max_annual_salary TEXT,
                type TEXT,
                platform TEXT,
                company TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(title, company, published_at)
            )
        """))
        conn.commit()
    logger.success("Table 'jobs' prête")


def load_existing_jobs():
    """Charge les signatures des jobs déjà en base"""
    engine = get_engine()
    existing = set()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT title, company, published_at FROM jobs"
            ))
            for row in result:
                sig = f"{row.title}|{row.company}|{row.published_at}"
                existing.add(sig)
        logger.info(f"{len(existing)} jobs existants en base")
    except Exception as e:
        logger.error(f"Erreur chargement jobs existants : {e}")
    return existing


def insert_jobs(jobs: list):
    """Insère les nouveaux jobs dans PostgreSQL"""
    engine = get_engine()
    inserted = 0
    with engine.connect() as conn:
        for job in jobs:
            try:
                d = asdict(job)
                conn.execute(text("""
                    INSERT INTO jobs (
                        title, description, location, candidate_profile,
                        published_at, experience_level, min_daily, max_daily,
                        min_annual_salary, max_annual_salary, type, platform, company
                    ) VALUES (
                        :title, :description, :location, :candidate_profile,
                        :published_at, :experience_level, :min_daily, :max_daily,
                        :min_annual_salary, :max_annual_salary, :type, :platform, :company
                    ) ON CONFLICT (title, company, published_at) DO NOTHING
                """), d)
                inserted += 1
            except Exception as e:
                logger.error(f"Erreur insertion job {job.title} : {e}")
        conn.commit()
    logger.success(f"{inserted} jobs insérés en base")