import json
from flask_lambda import FlaskLambda
import boto3
from botocore.errorfactory import ClientError
import os
from flask import request, redirect
from uuid import uuid4
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr

handler = FlaskLambda(__name__)
s3 = boto3.client("s3")
bucketName = os.environ["BUCKET_NAME"]
dynamoDB = boto3.resource("dynamodb")
tableName = dynamoDB.Table(os.environ["DYNAMO_TABLE_NAME"])

@handler.route('/')
def index():
    response = {"message": " Bienvenue sur le site de partage"}
    return (
        json.dumps(response),
        200,
        {'Content-Type':'application/json'}
    )
@handler.route('/objects', methods=['GET'])
def listobject():
    response = s3.list_objects_v2(Bucket= bucketName)["Contents"]
    return (
        json.dumps(response,indent=4, sort_keys=True, default=str),
        200,
        {'Content-Type':'application/json'}
    )
@handler.route("/shares", methods =["GET", "POST", "DELETE"])
def list_or_put_object():

    if request.method == "GET":
        response = tableName.scan()["Items"]
        return (
            json.dumps(response),
            200,
            {'Content-Type':'application/json'}
        )
    elif request.method == "POST":
        s3_key = request.get_json()["s3_key"]
        try:
            s3.head_object(Bucket= bucketName, Key= s3_key)
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return (
                    {"message":"key not found"},
                    404,
                    {'Content-Type':'application/json'}
                    )
        else:   
            now = datetime.now()
            dateAnTime = now.strftime("%d-%m-%Y %H:%M:%S")
            short_key = str(uuid4())[:10].replace("-", "")
            response = tableName.put_item(Item = {"s3_key": s3_key, "short_key": short_key,"Creation_Date": dateAnTime})
            return (
                {"short_key":short_key},
                200,
                {'Content-Type':'application/json'}
                )
    else:
        s3_key = request.get_json()["s3_key"]
        short_key = request.get_json()["short_key"]
        response = tableName.delete_item(Key = {"s3_key" : s3_key,"short_key": short_key })
        return (
            json.dumps({"message": "object deleted successfull"}),
            200,
            {'Content-Type':'application/json'}
            )

@handler.route("/download", methods =["GET"])
def dowload_object():

    short_key = request.args.get("short_key")
    s3_key = request.args.get("s3_key")
    record = tableName.query( KeyConditionExpression=Key('s3_key').eq(s3_key) & Key('short_key').eq(short_key))["Items"]
    if len(record) != 0:
        response = s3.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucketName,
                                                            'Key': s3_key},
                                                    ExpiresIn=300)
          
        return  (redirect(response),
                302,
                {'Content-Type':'application/json'}
                )
    else:
        return (
            {"message":"404 not found"},
            404,
            {'Content-Type':'application/json'}
            )

    