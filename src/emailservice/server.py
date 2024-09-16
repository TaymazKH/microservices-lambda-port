import base64

import grpc
from google.protobuf import json_format
from grpc_status import rpc_status

from dummy_email_service import DummyEmailService as Service
from genproto import demo_pb2 as pb

EMAIL_SERVICE = "greeter"
SEND_ORDER_CONFIRMATION_RPC = "say-hello"


class RequestContext:
    def __init__(self, method, path):
        self.http = {"method": method, "path": path}


class RequestData:
    def __init__(self, body, headers, request_context, is_base64_encoded):
        self.body = body
        self.headers = headers
        self.request_context = request_context
        self.is_base64_encoded = is_base64_encoded


class ResponseData:
    def __init__(self, status_code, headers, body, is_base64_encoded):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.is_base64_encoded = is_base64_encoded


def handle_request(msg, req_data):
    return Service.SendOrderConfirmation(msg)


def decode_request(req_data):
    if req_data['isBase64Encoded']:
        bin_req_body = base64.b64decode(req_data['body'])
    else:
        bin_req_body = req_data['body'].encode()

    if req_data['requestContext']['http']['path'] == f"/{EMAIL_SERVICE}/{SEND_ORDER_CONFIRMATION_RPC}":
        msg = pb.SendOrderConfirmationRequest()
    else:
        raise ValueError(f"Unknown path: {req_data['requestContext']['http']['path']}")

    json_format.Parse(bin_req_body.decode(), msg)
    return msg, RequestData(**req_data)


def encode_response(msg, rpc_error=None):
    if rpc_error is None:
        bin_resp_body = msg.SerializeToString()
        encoded_resp_body = base64.b64encode(bin_resp_body).decode()

        resp_data = ResponseData(
            status_code=200,
            headers={"Content-Type": "application/octet-stream", "Grpc-Code": str(grpc.StatusCode.OK.value[0])},
            body=encoded_resp_body,
            is_base64_encoded=True
        )
    else:
        status = rpc_status.to_status(rpc_error)
        resp_data = ResponseData(
            status_code=200,
            headers={"Content-Type": "text/plain", "Grpc-Code": str(status.code)},
            body=status.message,
            is_base64_encoded=False
        )

    return resp_data


def main(event, context):
    req_msg, req_data = decode_request(event)

    try:
        resp_msg = handle_request(req_msg, req_data)
        response = encode_response(resp_msg)
    except grpc.RpcError as err:
        response = encode_response(None, rpc_error=err)

    return response
