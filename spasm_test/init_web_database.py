from spasm.web import db, app

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()