from sqlmodel import SQLModel, create_engine

ROUTE_DATABASE_URL = "sqlite:///./route.db" 
POINTS_DATABASE_URL = "sqlite:///./points.db"

route_engine = create_engine(
    ROUTE_DATABASE_URL,
    echo = True  # shows SQL in console
)

points_engine = create_engine(
    POINTS_DATABASE_URL,
    echo = True
)

def init_db():
    SQLModel.metadata.create_all(route_engine) # create tables for routing logs
    SQLModel.metadata.create_all(points_engine) # create tables for points of interest
