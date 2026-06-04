from app.extensions import db

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    
    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )
    
    first_name = db.Column(
        db.String(100),
        nullable=True
    )
    
    last_name = db.Column(
        db.String(100),
        nullable=True
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True
    )
    
    password_hash = db.Column(
        db.String(255),
        nullable=False
    )
    
    role = db.Column(
        db.String(50),
        nullable=False,
        default="operator"
    )
    
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )
    
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )
    