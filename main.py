import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

load_dotenv()

app = Flask(__name__)


app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)
ma = Marshmallow(app)

# ==========================================
# DATABASE MODELS
# ==========================================

order_product = db.Table(
    "order_product",
    db.Column("order_id", db.Integer, db.ForeignKey("order.id"), primary_key=True),
    db.Column("product_id", db.Integer, db.ForeignKey("product.id"), primary_key=True),
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255))
    email = db.Column(db.String(100), unique=True, nullable=False)
    orders = db.relationship("Order", backref="user", cascade="all, delete-orphan")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_date = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    products = db.relationship(
        "Product", secondary=order_product, backref=db.backref("orders", lazy="dynamic")
    )


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)


# ==========================================
# MARSHMALLOW SCHEMAS
# ==========================================


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True


class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        load_instance = True


class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        include_fk = True
        load_instance = True


user_schema = UserSchema()
users_schema = UserSchema(many=True)
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)


# ==========================================
# USER ENDPOINTS
# ==========================================


@app.route("/users", methods=["POST"])
def create_user():
    try:
        new_user = user_schema.load(request.json, session=db.session)
        db.session.add(new_user)
        db.session.commit()
        return user_schema.jsonify(new_user), 201
    except ValidationError as err:
        return jsonify({"validation_errors": err.messages}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "A user with that email already exists."}), 409


@app.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return users_schema.jsonify(users), 200


@app.route("/users/<int:id>", methods=["GET"])
def get_user(id):
    user = User.query.get_or_404(id)
    return user_schema.jsonify(user), 200


@app.route("/users/<int:id>", methods=["PUT"])
def update_user(id):
    user = User.query.get_or_404(id)
    try:
        updated_user = user_schema.load(
            request.json, instance=user, session=db.session, partial=True
        )
        db.session.commit()
        return user_schema.jsonify(updated_user), 200
    except ValidationError as err:
        return jsonify({"validation_errors": err.messages}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            {"error": "Database constraint violated (e.g., email already in use)."}
        ), 409


@app.route("/users/<int:id>", methods=["DELETE"])
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted successfully"}), 200


# ==========================================
# PRODUCT ENDPOINTS
# ==========================================


@app.route("/products", methods=["POST"])
def create_product():
    try:
        new_product = product_schema.load(request.json, session=db.session)
        db.session.add(new_product)
        db.session.commit()
        return product_schema.jsonify(new_product), 201
    except ValidationError as err:
        return jsonify({"validation_errors": err.messages}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Invalid product data."}), 400


@app.route("/products/<int:id>", methods=["GET"])
def get_product(id):
    product = Product.query.get_or_404(id)
    return product_schema.jsonify(product), 200


@app.route("/products", methods=["GET"])
def get_products():

    page = request.args.get("page", 1, type=int)

    per_page = request.args.get("per_page", 5, type=int)

    paginated_products = Product.query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "products": products_schema.dump(paginated_products.items),
            "total_items": paginated_products.total,
            "total_pages": paginated_products.pages,
            "current_page": paginated_products.page,
        }
    ), 200


@app.route("/products/<int:id>", methods=["PUT"])
def update_product(id):
    product = Product.query.get_or_404(id)
    try:
        updated_product = product_schema.load(
            request.json, instance=product, session=db.session, partial=True
        )
        db.session.commit()
        return product_schema.jsonify(updated_product), 200
    except ValidationError as err:
        return jsonify({"validation_errors": err.messages}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Database constraint violated."}), 409


@app.route("/products/<int:id>", methods=["DELETE"])
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted successfully"}), 200


# ==========================================
# ORDER ENDPOINTS
# ==========================================


@app.route("/orders", methods=["POST"])
def create_order():
    try:
        new_order = order_schema.load(request.json, session=db.session)
        db.session.add(new_order)
        db.session.commit()
        return order_schema.jsonify(new_order), 201
    except ValidationError as err:
        return jsonify({"validation_errors": err.messages}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            {"error": "Invalid user_id or database constraint violated."}
        ), 400


@app.route("/orders/user/<int:user_id>", methods=["GET"])
def get_user_orders(user_id):
    User.query.get_or_404(user_id)
    orders = Order.query.filter_by(user_id=user_id).all()
    return orders_schema.jsonify(orders), 200


@app.route("/orders/<int:order_id>/add_product/<int:product_id>", methods=["PUT"])
def add_product_to_order(order_id, product_id):
    order = Order.query.get_or_404(order_id)
    product = Product.query.get_or_404(product_id)

    if product in order.products:
        return jsonify({"message": "Product already exists in this order."}), 400

    order.products.append(product)
    db.session.commit()
    return jsonify(
        {"message": f"Product '{product.product_name}' added to order {order.id}"}
    ), 200


@app.route("/orders/<int:order_id>/remove_product/<int:product_id>", methods=["DELETE"])
def remove_product_from_order(order_id, product_id):
    order = Order.query.get_or_404(order_id)
    product = Product.query.get_or_404(product_id)

    if product not in order.products:
        return jsonify({"message": "Product not found in this order."}), 400

    order.products.remove(product)
    db.session.commit()
    return jsonify(
        {"message": f"Product '{product.product_name}' removed from order {order.id}"}
    ), 200


@app.route("/orders/<int:order_id>/products", methods=["GET"])
def get_order_products(order_id):
    order = Order.query.get_or_404(order_id)
    return products_schema.jsonify(order.products), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
    app.run(debug=True)
