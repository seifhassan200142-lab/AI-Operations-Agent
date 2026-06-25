from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Customer, SupportTicket, Task
from app.db.seed import seed_database


def test_database_seeding_creates_sample_data():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    seed_database(db)

    assert db.query(Customer).count() >= 3
    assert db.query(SupportTicket).count() >= 5
    assert db.query(Task).count() >= 2
    db.close()
