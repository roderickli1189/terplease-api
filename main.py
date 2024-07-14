from flask import request, jsonify, Flask
from config import app, db
from models import Listing, User
from datetime import datetime
import bcrypt
import base64
import os
import http.client
import requests
import json

from os import environ as env

from dotenv import load_dotenv, find_dotenv
from authlib.integrations.flask_oauth2 import ResourceProtector
from validator import Auth0JWTBearerTokenValidator

require_auth = ResourceProtector()
validator = Auth0JWTBearerTokenValidator(
    os.getenv('AUTH0_DOMAIN'),
    os.getenv('AUTH0_API_AUDIENCE')
)
require_auth.register_token_validator(validator)

@app.route("/")
def index():
    return "Hello World"
    
@app.route("/get_phone/<user_id>", methods=["GET"])
@require_auth("read:user_phone")
def get_phone(user_id):
    user = User.query.filter_by(sub=user_id).first()
    if not user:
        return jsonify({"message": "user doesn't exist"}), 404
    return jsonify({"phoneNumber":user.phone_number}), 200

@app.route("/delete_listing/<listing_id>", methods=["DELETE"])
@require_auth("delete:listing")
def delete_listing(listing_id):
    print(listing_id)
    listing = db.session.get(Listing, listing_id)
    if not listing:
        return jsonify({"message": "Listing not found"}), 404
    else:
        db.session.delete(listing)  # Mark the listing for deletion
        db.session.commit()
        return jsonify({"message": "Listing deleted"}), 200
    
@app.route("/update_listing", methods=["PATCH"])
@require_auth("update:listing")
def update_listing():
    try:
        data = request.get_json()
        listing_id = data.get("id")
        listing = db.session.get(Listing, listing_id)

        if not listing:
            return jsonify({"message": "Listing not found"}), 404

        listing.apartment = data.get("apartment") if data.get("apartment") else listing.apartment
        listing.rent = data.get("rent") if data.get("rent") else listing.rent
        listing.lay_out = data.get("layOut") if data.get("layOut") else listing.lay_out
        listing.description = data.get("description") if data.get("description") else listing.description
        listing.gender = data.get("gender") if data.get("gender") else listing.gender
        listing.semester = data.get("semester") if data.get("semester") else listing.semester
        listing.images = data.get("images") if data.get("images") else listing.images

        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            listing.start_date = start_date
            listing.end_date = end_date
        
        # Save the changes to the database
        db.session.commit()

        # Return the updated listing
        return jsonify({"message": "works!"}), 200

    except Exception as e:
        return jsonify({"message": "An error occurred", "error": str(e)}), 500

@app.route("/update_profile", methods=["PATCH"])
@require_auth("update:user")
def update_profile():

    # getting auth0 management token
    client_secret = os.getenv("API_CLIENT_SECRET")
    sub = request.json.get("id")
    name = request.json.get("name")
    nickname = request.json.get("nickname")
    phoneNumber = request.json.get("phoneNumber")
    cpy = phoneNumber
    parts = phoneNumber.split("-")
    phoneNumber = "+1" + ''.join(parts)
    user = User.query.filter_by(sub=sub).first()

    url = os.getenv("AUTH0_TOKEN_URL")
    headers = {'content-type': "application/x-www-form-urlencoded"}
    
    payload = {
        'grant_type': 'client_credentials',
        'client_id': os.getenv('AUTH0_CLIENT_ID'),
        'client_secret': client_secret,
        'audience': os.getenv('AUTH0_TOKEN_AUDIENCE')
    }
    
    response = requests.post(url, data=payload, headers=headers)
    token_data = response.json()
    
    if response.status_code == 200:
        access_token = token_data.get("access_token")

        url = os.getenv('AUTH0_UPDATE_USER_URL') + sub

        payload = {}

        if name != "":
            payload["name"] = name
        if nickname != "":
            payload["nickname"] = nickname
        if phoneNumber != "":
            payload["user_metadata"] = { "phoneNumber": phoneNumber}

        payload_json = json.dumps(payload)

        headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
        }

        response = requests.request("PATCH", url, headers=headers, data=payload_json)
        response_data = response.json()

         # Check if the update was successful
        if response.status_code == 200:
            
            # updating the user on our side
            if name != "":
                user.name = name
            if nickname != "":
                user.nickname = nickname
            if cpy != "":
                user.phone_number = cpy
            db.session.commit()

            message = "User profile updated successfully"
            return jsonify(message=message)
        else:
            message = f"Failed to update user profile: {response_data.get('message', 'Unknown error')}"
            return jsonify(error=message), response.status_code
    else:
        # Handle error in obtaining token
        return jsonify(error="Failed to obtain token"), response.status_code 

@app.route("/listings", methods=["GET"])
def get_listings():
    listings = Listing.query.all()
    json_listings = list(map(lambda x: x.to_json(), listings))
    return jsonify({"listings": json_listings})

@app.route("/listings/<listing_id>", methods=["GET"])
def get_listing_id(listing_id):
    listing = db.session.get(Listing, listing_id)
    if not listing:
        return jsonify({"error": "Listing not found"}), 404
    
    return jsonify(listing.to_json())

@app.route("/user_listings/<user_id>", methods=["GET"])
def get_user_listings(user_id):
    user = User.query.filter_by(sub=user_id).first()
    if not user:
        return jsonify({"error": "Listing not found"}), 404
    return jsonify(user.get_listing())

@app.route("/create_listing", methods=["POST"])
@require_auth("create:listing")
def create_listing():
    apartment = request.json.get("apartment")
    rent = int(request.json.get("rent"))
    lay_out = request.json.get("layOut")
    description = request.json.get("description")
    gender = request.json.get("gender")
    semester = request.json.get("semester")

    start_date = request.json.get("start_date")
    end_date = request.json.get("end_date")
    post_date = request.json.get("postDate")

    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    post_date = datetime.strptime(post_date, '%Y-%m-%d %H:%M:%S')
    
    images = request.json.get("images") 

    sub = request.json.get("userSub")
    user = User.query.filter_by(sub=sub).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    if len(user.listings) >= 2:
        return jsonify({"message": "cannot have more than two listings at once"}), 404

    new_listing = Listing(apartment=apartment, rent=rent, lay_out=lay_out, description=description,
                         gender=gender, semester=semester, start_date=start_date, end_date=end_date,
                         post_date=post_date, images=images, user=user)

    try:
        db.session.add(new_listing)
        db.session.commit()
    except Exception as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"message": "listing created"}), 201

@app.route("/create_account", methods=["POST"])
def create_account():
    name = request.json.get("name")
    sub = request.json.get("sub")
    email = request.json.get("email")
    picture = request.json.get("picture")
    nickname = request.json.get("nickname")
    phone_number = request.json.get("phoneNumber")

    try:
        unique_user = User.query.filter_by(sub=sub).first()
        if unique_user:
            return jsonify({"message": "user already exists"}), 409
        
        new_user = User(name=name, sub=sub, email=email, picture=picture, nickname=nickname, phone_number=phone_number)
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({"message": "account created"}), 201
    
    except Exception as e:
        return jsonify({"message": str(e)}), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)

# no longer needed code

'''
@app.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    json_users = list(map(lambda x: x.to_json(), users))
    return jsonify({"users": json_users})

@app.route("/create_account", methods=["POST"])
def create_account():
    username = request.json.get("username")
    password = request.json.get("password")
    email = request.json.get("email")

    unique_user = User.query.filter_by(username=username).first()
    if unique_user:
        return jsonify({"message" : "username already taken", "err" : "username"}), 400

    unique_email = User.query.filter_by(email=email).first()
    if unique_email:
        return jsonify({"message" : "email already taken", "err" : "email"}), 400
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    new_user = User(username=username, email=email, password = hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message" : "account created"}), 201

@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username")
    password = request.json.get("password")
    user = User.query.filter_by(username=username).first()

    if user:
        if bcrypt.checkpw(password.encode('utf-8'), user.password):
            return jsonify({"message": "Login successful"}), 200
        else:
            return jsonify({"message": "Wrong username or password", "err": "root"}), 400
    else:
        return jsonify({"message": "Wrong username or password", "err": "root"}), 400
    


@app.route('/delete_all_users', methods=['DELETE'])
def delete_all_users():
    try:
        # Execute a query to delete all rows from the User table
        db.session.query(User).delete()
        db.session.commit()
        return jsonify({"message" : "deleted"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f'Error deleting users: {str(e)}'}), 500

if __name__ == "__main__":
    with app.app_context():
        # Drop all tables
        db.drop_all()

        # Recreate the tables
        db.create_all()
'''