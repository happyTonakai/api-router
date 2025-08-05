#!/usr/bin/env python
# coding=UTF-8
"""
Author: Zerui Han <hanzr.nju@outlook.com>
Date: 2025-08-05 21:59:43
Description:
FilePath: /api-router/app.py
LastEditTime: 2025-08-05 22:54:41
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

    try:
        api_key = config.get_next_key(provider)
        base_url = config.get_base_url(provider)

        target_url = f"{base_url}{path}"

        headers = dict(request.headers)
        headers.pop("Host", None)
        # Remove existing Authorization header if it's for Gemini
        headers.pop("Authorization", None)

        params = dict(request.args)  # Start with existing query parameters

        # --- IMPORTANT CHANGE FOR GEMINI AUTHENTICATION ---
        if provider == "gemini":
            params["key"] = api_key  # Add API key as a query parameter
            # For Gemini, you generally don't need the "Authorization" header
            # if sending the key as a query param.
            # If the base URL changes to a Vertex AI endpoint,
            # you might need ADC or a different header.
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
        logger.debug(f"[{request_id}] Request headers: {dict(headers)}")
        if request.is_json:
            logger.debug(f"[{request_id}] Request JSON: {request.get_json()}")
        if params:  # Log the updated parameters
            logger.debug(f"[{request_id}] Request params: {dict(params)}")

        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=params,  # Use the updated parameters
            json=request.get_json() if request.is_json else None,
            data=request.get_data() if not request.is_json else None,
            stream=True,
            timeout=300,
        )

        duration = time.time() - start_time
        logger.info(f"[{request_id}] Response received: {response.status_code} ({duration:.2f}s)")
        logger.debug(f"[{request_id}] Response headers: {dict(response.headers)}")

        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        excluded_headers = ["content-length", "connection"]
        headers_to_forward = [
            (name, value)
            for (name, value) in response.raw.headers.items()
            if name.lower() not in excluded_headers
        ]

        return Response(generate(), status=response.status_code, headers=headers_to_forward)

    except requests.exceptions.RequestException as e:
        duration = time.time() - start_time
        logger.error(f"[{request_id}] Request failed after {duration:.2f}s: {str(e)}")
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
