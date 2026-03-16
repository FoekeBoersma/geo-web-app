from sqlmodel import SQLModel, create_engine

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL,
    echo = True  # shows SQL in console
)

def init_db():
    SQLModel.metadata.create_all(engine)
