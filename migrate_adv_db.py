import os
from sqlalchemy import create_engine
from database import Base, db_path

def migrate():
    print(f"Migrating database at {db_path}...")
    engine = create_engine(f'sqlite:///{db_path}', echo=True)
    # create_all will only create tables that do not exist yet.
    Base.metadata.create_all(engine)
    print("Migration successful! New tables created.")

if __name__ == '__main__':
    migrate()
