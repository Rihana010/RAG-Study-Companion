from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.documents import documents_bp
    from app.routes.youtube import youtube_bp
    from app.routes.chat import chat_bp
    from app.routes.study import study_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    app.register_blueprint(youtube_bp, url_prefix='/api/youtube')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(study_bp, url_prefix='/api/study')
    
    return app
