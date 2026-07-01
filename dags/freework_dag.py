from airflow.sdk import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys

# ── Ajoute le dossier scraper au path ─────────────────
sys.path.insert(0, '/opt/airflow/scraper')


# ── Configuration par défaut ───────────────────────────
default_args = {
    'owner': 'airflow',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='freework_scraper',
    default_args=default_args,
    description='Scrape Freework et charge dans PostgreSQL',
    schedule='0 8 * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['scraping', 'freework'],
) as dag:

    def task_create_table():
        from database import create_table          
        create_table()

    def task_scrape():
        import time, random
        from main import fetch_page_data, create_job_instances  
        from database import load_existing_jobs, insert_jobs    

        page = 1
        consecutive_duplicates = 0
        MAX_CONSECUTIVE_DUPLICATES = 2

        while True:
            data = fetch_page_data(page=page)
            if not data or not data.get("hydra:member"):
                break

            jobs = create_job_instances(data["hydra:member"])
            existing = load_existing_jobs()
            signatures = [f"{j.title}|{j.company}|{j.published_at}" for j in jobs]

            duplicates = sum(1 for s in signatures if s in existing)
            dup_pct = (duplicates / len(signatures)) * 100 if signatures else 0

            if dup_pct == 100:
                consecutive_duplicates += 1
                if consecutive_duplicates >= MAX_CONSECUTIVE_DUPLICATES:
                    break
            else:
                consecutive_duplicates = 0
                new_jobs = [j for j, s in zip(jobs, signatures) if s not in existing]
                if new_jobs:
                    insert_jobs(new_jobs)

            page += 1
            time.sleep(random.uniform(3, 10))

    def task_check():
        from database import load_existing_jobs                 
        existing = load_existing_jobs()
        print(f" Total jobs en base : {len(existing)}")

    t1 = PythonOperator(task_id='creer_table',      python_callable=task_create_table)
    t2 = PythonOperator(task_id='scraper_freework', python_callable=task_scrape)
    t3 = PythonOperator(task_id='verifier_donnees', python_callable=task_check)

    t1 >> t2 >> t3