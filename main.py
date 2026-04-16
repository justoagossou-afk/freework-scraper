import requests
import os
import sys
from dotenv import load_dotenv
from loguru import logger
from dataclasses import dataclass, field, asdict
from datetime import datetime
import time
import random
import html
import re
from sqlalchemy import create_engine, text

logger.remove()
logger.add(sys.stderr, level='INFO')

load_dotenv()

# ─── Config base de données ───────────────────────────────────────
DB_USER     = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME     = os.getenv("POSTGRES_DB")
DB_HOST     = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT     = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ─── Config scraper ───────────────────────────────────────────────
HEADERS = {
    "User-Agent": os.getenv("USER_AGENT"),
    "Accept": "application/ld+json",
    "Accept-Language": "fr",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.free-work.com/fr/tech-it/jobs"
}

PARAMS = {
    "page": 1,
    "itemsPerPage": 16,
    "locationKeys": "fr~~~",
    "searchKeywords": "data"
}

URL = 'https://www.free-work.com/api/job_postings'


# ─── Dataclass ────────────────────────────────────────────────────
@dataclass
class Job():
    title: str
    description: str
    location: str
    candidate_profile: str
    published_at: str
    experience_level: str
    min_daily: int = field(default='N/A')
    max_daily: int = field(default='N/A')
    min_annual_salary: int = field(default='N/A')
    max_annual_salary: int = field(default='N/A')
    type: str = field(default='N/A')
    platform: str = field(default='Freework')
    company: str = field(default='N/A')


# ─── Base de données ──────────────────────────────────────────────
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


# ─── Scraping ─────────────────────────────────────────────────────
def fetch_page_data(page=1):
    """Récupère les données d'une page"""
    try:
        with requests.Session() as s:
            params = PARAMS.copy()
            params["page"] = page
            r = s.get(url=URL, params=params, headers=HEADERS)
            r.raise_for_status()
            data = r.json()
            if data:
                logger.success(f'Page {page} récupérée')
                return data
            else:
                logger.warning('Data vide')
                return None
    except requests.RequestException as e:
        logger.error(f'Erreur requête page {page}: {e}')
        return None


def clean_html_text(text):
    """Nettoie le texte HTML"""
    if not text:
        return 'N/A'
    text = text.encode().decode('unicode_escape')
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = ' '.join(text.split())
    return text


def create_job_instances(data) -> list:
    """Crée une liste d'instances Job"""
    jobs = []
    for item in data:
        location = item.get('location', {}).get('label') or 'N/A'
        description = clean_html_text(item.get('description')) or 'N/A'
        company = item.get('company', {}).get('name') or 'N/A'

        published_at = item.get('publishedAt')
        if published_at:
            try:
                published_at = datetime.fromisoformat(
                    published_at).strftime('%Y-%m-%d')
            except (ValueError, AttributeError):
                published_at = 'N/A'
        else:
            published_at = 'N/A'

        job = Job(
            title=item.get('title') or 'N/A',
            description=description,
            location=location,
            candidate_profile=clean_html_text(
                item.get('candidateProfile')) or 'N/A',
            published_at=published_at,
            experience_level=item.get('experienceLevel') or 'N/A',
            min_daily=item.get('minDailySalary', 'N/A'),
            max_daily=item.get('maxDailySalary', 'N/A'),
            min_annual_salary=item.get('minAnnualSalary', 'N/A'),
            max_annual_salary=item.get('maxAnnualSalary', 'N/A'),
            company=company
        )
        jobs.append(job)
        logger.success(f"Job traité : {job.title} chez {company}")
    return jobs


# ─── Main ─────────────────────────────────────────────────────────
def main():
    logger.info("Démarrage du scraper Freework → PostgreSQL")

    # Créer la table si elle n'existe pas
    create_table()

    page = 1
    consecutive_duplicates = 0
    MAX_CONSECUTIVE_DUPLICATES = 2

    while True:
        logger.info(f'Page {page} en cours...')
        data = fetch_page_data(page=page)

        if not data or not data.get("hydra:member"):
            logger.info('Plus de données.')
            break

        jobs = create_job_instances(data["hydra:member"])
        existing = load_existing_jobs()
        signatures = [f"{j.title}|{j.company}|{j.published_at}" for j in jobs]

        duplicates = sum(1 for s in signatures if s in existing)
        dup_pct = (duplicates / len(signatures)) * 100 if signatures else 0
        logger.info(f"Page {page} : {duplicates}/{len(signatures)} doublons ({dup_pct:.1f}%)")

        if dup_pct == 100:
            consecutive_duplicates += 1
            if consecutive_duplicates >= MAX_CONSECUTIVE_DUPLICATES:
                logger.info("Arrêt : trop de doublons consécutifs.")
                break
        else:
            consecutive_duplicates = 0
            new_jobs = [j for j, s in zip(jobs, signatures) if s not in existing]
            if new_jobs:
                insert_jobs(new_jobs)

        page += 1
        delay = random.uniform(3, 10)
        logger.info(f'Pause {delay:.1f}s...')
        time.sleep(delay)

    logger.success(f'Scraping terminé — {page - 1} pages traitées')


if __name__ == '__main__':
    main()