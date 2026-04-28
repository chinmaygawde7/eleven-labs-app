import os
from flask import Flask
from flask_session import Session
from app.config import Config

def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"),
        static_url_path="/static",
        template_folder="templates",
    )
    app.config.from_object(Config)

    Session(app)

    from app.blueprints.auth     import auth_bp
    from app.blueprints.voice    import voice_bp
    from app.blueprints.schedule import schedule_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(schedule_bp)

    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        from app.services.scheduler import start_scheduler
        start_scheduler()

    return app