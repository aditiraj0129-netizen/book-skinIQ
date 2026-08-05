"""
Seeds the database with an admin user and a starter set of services.
Run with: python -m app.seed
Idempotent — safe to re-run.
"""
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.booking import AdminUser, Service
from app.models.business import BusinessSettings, Review

settings = get_settings()

SERVICES = [
    dict(name="Consultation", description="30-min general consultation", duration_minutes=30, price=25),
    dict(name="Haircut", description="Classic haircut & style", duration_minutes=45, price=35),
    dict(name="Deep Tissue Massage", description="60-min therapeutic massage", duration_minutes=60, price=80),
    dict(name="Skin Facial", description="Rejuvenating facial treatment", duration_minutes=45, price=60),
]

REVIEWS = [
    dict(customer_name="Priya N.", rating=5, comment="Booked in seconds and the calendar made it obvious which slots were free. Massage was excellent too."),
    dict(customer_name="Jordan M.", rating=5, comment="Loved that I could ask the assistant about their cancellation policy before booking. No surprises."),
    dict(customer_name="Aisha K.", rating=4, comment="Great haircut, would've liked a few more evening slots."),
    dict(customer_name="Tom R.", rating=5, comment="The reschedule flow saved me — moved my facial with two taps when my plans changed."),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(AdminUser).filter(AdminUser.username == settings.admin_username).first():
            db.add(
                AdminUser(
                    username=settings.admin_username,
                    hashed_password=hash_password(settings.admin_password),
                )
            )
            print(f"Created admin user '{settings.admin_username}'")

        for s in SERVICES:
            if not db.query(Service).filter(Service.name == s["name"]).first():
                db.add(Service(**s))
                print(f"Created service '{s['name']}'")
        db.commit()

        if not db.query(BusinessSettings).filter(BusinessSettings.id == "default").first():
            db.add(BusinessSettings(id="default"))
            print("Created default business settings")
            db.commit()

        if db.query(Review).count() == 0:
            services_by_name = {s.name: s for s in db.query(Service).all()}
            for i, r in enumerate(REVIEWS):
                service = list(services_by_name.values())[i % len(services_by_name)]
                db.add(Review(service_id=service.id, **r))
            print(f"Created {len(REVIEWS)} sample reviews")

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
