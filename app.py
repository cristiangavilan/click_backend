import os
from hashlib import md5
from datetime import datetime
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
from flask_jwt_extended import (
    JWTManager,
    get_jwt_identity,
    jwt_required,
    create_access_token,
)

ASSETS_FOLDER = "static/assets"
UPLOAD_FOLDER = "static/uploads"
load_dotenv()
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
CORS(app)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["ASSETS_FOLDER"] = ASSETS_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+pymysql://"
    + os.getenv("DB_USER")
    + ":"
    + os.getenv("DB_PASSWORD")
    + "@"
    + os.getenv("DB_HOST")
    + ":"
    + os.getenv("DB_PORT")
    + "/"
    + os.getenv("DB_NAME")
)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")

db = SQLAlchemy(app)
jwt = JWTManager(app)
pwkey = os.getenv("PASSWORD_KEY")


class Roles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    users = db.relationship("Users", backref="roles", lazy=True)


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    enable = db.Column(db.Boolean, nullable=False)
    imageProfile = db.Column(db.String(255), nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    roleId = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

    def toDict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "username": self.username,
            "enable": self.enable,
            "imageProfile": (
                self.imageProfile
                if self.imageProfile != ""
                else os.path.join(
                    request.host_url, app.config["ASSETS_FOLDER"], "user.png"
                ).replace("\\", "/")
            ),
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            # "roleId": self.roleId,
            "roleName": self.roles.query.filter_by(id=self.roleId).first().name,
        }


class Categories(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    products = db.relationship("Products", backref="categories", lazy=True)

    def getName(self, id):
        return Categories.query.filter_by(id=id).first().name

    def toDict(self):
        return {
            "id": self.id,
            "name": self.name,
            # "products": list(map(lambda product: product.toDict(), self.products)),
        }


class Products(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(1000), nullable=True)
    image = db.Column(db.String(255), nullable=False)
    count = db.Column(db.Integer, nullable=False)
    rate = db.Column(db.Numeric(2, 1), nullable=False)
    categoryId = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    def toDict(self):
        return {
            "id": self.id,
            "title": self.title,
            "price": self.price,
            "description": self.description,
            "image": self.image,
            "count": self.count,
            "rate": self.rate,
            "categoryId": self.categoryId,
            "categoryName": self.categories.getName(self.categoryId),
        }


@app.route("/register", methods=["POST"])
def register():

    userExists = Users.query.filter_by(username=request.json["username"]).first()
    if userExists:
        return jsonify(message="User already exists"), 409

    password = request.json["password"] + pwkey

    new_user = Users(
        name=request.json["name"],
        email=request.json["email"],
        username=request.json["username"],
        password=md5(password.encode()).hexdigest(),
        enable=request.json["enable"],
        imageProfile=request.json["imageProfile"],
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
        roleId=1,
    )

    db.session.add(new_user)
    db.session.commit()
    return jsonify(message="User registered successfully"), 201


@app.route("/login", methods=["POST"])
def login():
    userExists = Users.query.filter_by(username=request.json["username"]).first()
    if not userExists:
        return jsonify({"message": "Bad username or password"}), 404

    password = request.json["password"] + pwkey

    if userExists.password == md5(password.encode()).hexdigest():
        if not userExists.enable:
            return jsonify({"message": "User is disabled"}), 401
        access_token = create_access_token(identity=request.json["username"])
        return jsonify({"token": access_token}), 201
    else:
        return jsonify({"message": "Bad username or password"}), 404


@app.route("/user")
@jwt_required()
def getUser():
    current_user = get_jwt_identity()
    user = Users.query.filter_by(username=current_user).first()
    return jsonify(user.toDict()), 200


@app.route("/categories")
def getCategories():
    categories = Categories.query.all()
    categories = list(map(lambda category: category.toDict(), categories))
    print(jsonify(categories))
    return jsonify(categories), 200


@app.route("/categories", methods=["POST"])
@jwt_required()
def createCategory():
    name = request.json["name"]
    category = Categories.query.filter_by(name=name).first()

    if category:
        return jsonify(message=f"Category {name} already exists"), 409

    new_category = Categories(name=name)
    db.session.add(new_category)
    db.session.commit()
    return jsonify(message=f"Category {name} created successfully"), 201


@app.route("/products")
def getProducts():
    products = Products.query.all()
    products = list(map(lambda products: products.toDict(), products))
    print(jsonify(products))
    return jsonify(products), 200


@app.route("/products/<int:category_id>")
def getProductsByCategory(category_id):
    # products = Products.query.all()
    print(category_id)
    products = Products.query.filter_by(categoryId=category_id).all()
    products = list(map(lambda products: products.toDict(), products))
    print(jsonify(products))
    return jsonify(products), 200


@app.route("/products/<int:product_id>")
def getProduct(product_id):
    product = Products.query.filter_by(id=product_id).first()
    return jsonify(product.toDict()), 200


@app.route("/products", methods=["POST"])
@jwt_required()
def createProduct():

    new_product = Products(
        title=request.json["title"],
        price=request.json["price"],
        description=request.json["description"],
        image=request.json["image"],
        count=request.json["count"],
        rate=request.json["rate"],
        categoryId=request.json["categoryId"],
    )
    db.session.add(new_product)
    db.session.commit()
    return jsonify(message="Product created successfully"), 201


@app.route("/products", methods=["PUT"])
@jwt_required()
def modifyProduct():
    product_id = request.json["id"]
    update_fields = {
        "title": request.json["title"],
        "description": request.json["description"],
        "price": request.json["price"],
        "image": request.json["image"],
        "count": request.json["count"],
        "rate": request.json["rate"],
        "categoryId": request.json["categoryId"],
    }
    db.session.query(Products).filter(Products.id == product_id).update(update_fields)
    db.session.commit()
    return jsonify(message="Product modified successfully"), 201


@app.route("/products/<int:product_id>", methods=["DELETE"])
@jwt_required()
def deleteProduct(product_id):

    db.session.query(Products).filter(Products.id == product_id).delete()
    db.session.commit()
    return jsonify(message="Product deleted successfully"), 201


@app.route("/uploadimage", methods=["POST"])
@jwt_required()
def upload_file():
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400
    if file:
        filename = file.filename
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        file_url = os.path.join(
            request.host_url, app.config["UPLOAD_FOLDER"], filename
        ).replace("\\", "/")
        return jsonify({"message": "Image uploaded successfully", "url": file_url}), 201


if __name__ == "__main__":
    app.run(debug=True, port=4000)
