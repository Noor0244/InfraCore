from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Ensure all models are imported for SQLAlchemy relationship resolution (after Base is created)
def import_models():
    import app.models.user
    import app.models.project
    import app.models.project_alignment
    import app.models.material
    import app.models.material_vendor
    import app.models.activity
    import app.models.road_stretch
    import app.models.material_activity
    import app.models.material_stretch
    try:
        import app.models.stretch_relationship_patch
    except ImportError:
        pass

# Call this in env.py or other initialization contexts
try:
    import_models()
except ImportError:
    pass
