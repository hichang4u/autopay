from app import app, db
from flask_migrate import Migrate
from app.models.document import Document, DocumentTemplate, DocumentHistory

migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run(debug=True) 