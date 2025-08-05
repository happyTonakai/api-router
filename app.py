#!/usr/bin/env python
# coding=UTF-8
"""
Author: Zerui Han <hanzr.nju@outlook.com>
Date: 2025-08-05 21:59:43
Description:
FilePath: /api-router/app.py
LastEditTime: 2025-08-05 23:50:33
"""
import logging
import time

import requests
from flask import Flask, Response, jsonify, request

from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
config = Config()


def forward_request(provider: str, path: str) -> Response:
    start_time = time.time()
    request_id = f"{provider}-{int(time.time() * 1000)}"

    # --- Debugging: Log incoming request details ---
    logger.debug(f"[{request_id}] Incoming method: {request.method}")
    logger.debug(f"[{request_id}] Incoming path: {path}")
    logger.debug(f"[{request_id}] Incoming headers: {dict(request.headers)}")
    if request.method in ["POST", "PUT", "PATCH"]:
        if request.is_json:
            try:
                # Attempt to get JSON, but catch error if malformed
                logger.debug(
                    f"[{request_id}] Incoming request body (JSON): {request.get_json(silent=True)}"
                )
            except Exception as e:
                logger.warning(f"[{request_id}] Could not parse incoming JSON body: {e}")
                # Don't return error here, let the original request.get_json() handle it if needed later
        else:
            logger.debug(f"[{request_id}] Incoming request body (raw data): {request.get_data()}")
    # --- End Debugging ---

    try:
        api_key = config.get_next_key(provider)
        base_url = config.get_base_url(provider)

        target_url = f"{base_url}{path}"

        headers = dict(request.headers)
        headers.pop("Host", None)
        headers.pop("Authorization", None)  # Remove any existing auth header

        # --- IMPORTANT: Remove x-goog-api-key if present ---
        # The client is sending this, but we want to use the query param for Gemini.
        headers.pop("x-goog-api-key", None)
        # --- End IMPORTANT ---

        params = dict(request.args)  # Start with existing query parameters

        # --- IMPORTANT CHANGE FOR GEMINI AUTHENTICATION ---
        if provider == "gemini":
            params["key"] = api_key  # Add API key as a query parameter
            # For Gemini, you generally don't need the "Authorization" header
            # if sending the key as a query param.
        else:
            # For other providers, use the Authorization Bearer header
            headers["Authorization"] = f"Bearer {api_key}"
        # --- END IMPORTANT CHANGE ---

        # Add provider-specific headers
        if provider == "openrouter":
            headers["HTTP-Referer"] = "http://localhost:9999"
            headers["X-Title"] = "API Router"

        # Log request details
        logger.info(
            f"[{request_id}] Forwarding {request.method} request to {provider}: {target_url}"
        )
        logger.debug(f"[{request_id}] Request headers (after modification): {dict(headers)}")
        if params:
            logger.debug(f"[{request_id}] Request params (after modification): {dict(params)}")

        # Read request body only for methods that typically have one
        request_body_json = None
        request_body_data = None

        # The error "Failed to decode JSON object" was coming from Flask trying to parse
        # a GET request with Content-Type: application/json.
        # This block ensures we only try to parse JSON for POST/PUT/PATCH.
        if request.method in ["POST", "PUT", "PATCH"]:
            if request.is_json:
                try:
                    request_body_json = request.get_json()
                    logger.debug(f"[{request_id}] Request JSON: {request_body_json}")
                except Exception as e:
                    logger.error(
                        f"[{request_id}] Failed to parse incoming JSON for {request.method} request: {e}"
                    )
                    return jsonify({"error": f"Invalid JSON in request body: {e}"}), 400
            else:
                request_body_data = request.get_data()
                if request_body_data:
                    logger.debug(f"[{request_id}] Request data: {request_body_data}")
        # Note: For GET requests, request_body_json and request_body_data will remain None,
        # which is correct for requests.request().

        # Determine if it's a streaming request.
        is_streaming_endpoint = "/generateContent" in path or "/chat/completions" in path

        # Make the request
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=params,
            json=request_body_json,  # Pass the conditionally parsed JSON
            data=request_body_data,  # Pass the conditionally read data
            stream=is_streaming_endpoint,
            timeout=300,
        )

        duration = time.time() - start_time
        logger.info(f"[{request_id}] Response received: {response.status_code} ({duration:.2f}s)")
        logger.debug(f"[{request_id}] Response headers: {dict(response.headers)}")

        excluded_headers = ["content-length", "connection", "content-encoding", "transfer-encoding"]
        headers_to_forward = [
            (name, value)
            for (name, value) in response.raw.headers.items()
            if name.lower() not in excluded_headers
        ]

        if is_streaming_endpoint:

            def generate_stream():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk

            return Response(
                generate_stream(), status=response.status_code, headers=headers_to_forward
            )
        else:
            content = response.content
            return Response(content, status=response.status_code, headers=headers_to_forward)

    except requests.exceptions.RequestException as e:
        duration = time.time() - start_time
        logger.error(f"[{request_id}] Request failed after {duration:.2f}s: {str(e)}")
        # Check if it's a bad status code from upstream
        if hasattr(e, "response") and e.response is not None:
            logger.error(
                f"[{request_id}] Upstream response status: {e.response.status_code}, content: {e.response.text}"
            )
            return (
                jsonify(
                    {"error": f"Upstream API error: {e.response.status_code} - {e.response.text}"}
                ),
                e.response.status_code,
            )
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[{request_id}] Unexpected error after {duration:.2f}s: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/<provider>/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.route("/<provider>/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.route("/<provider>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def route_request(provider: str, path: str = ""):
    logger.info(f"Received request for provider: {provider}, path: {path}")

    if provider not in config.get_providers():
        logger.warning(f"Unsupported provider requested: {provider}")
        return jsonify({"error": f"Provider {provider} not supported"}), 400

    return forward_request(provider, path)


@app.route("/", methods=["GET"])
def health_check():
    logger.info("Health check endpoint accessed")
    return jsonify({"status": "ok", "providers": config.get_providers()})


if __name__ == "__main__":
    logger.info("Starting API Router server on host 0.0.0.0, port 9999")
    logger.info(f"Available providers: {config.get_providers()}")
    app.run(host="0.0.0.0", port=9999, debug=True)
