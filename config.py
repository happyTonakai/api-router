#!/usr/bin/env python
# coding=UTF-8
"""
Author: Zerui Han <hanzr.nju@outlook.com>
Date: 2025-08-05 21:59:31
Description:
FilePath: /api-router/config.py
LastEditTime: 2025-08-05 22:18:45
"""
import os
from typing import Any, Dict, List

import yaml


class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.key_indices: dict[str, int] = {}
        self._initialize_key_indices()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    def _initialize_key_indices(self):
        for provider in self.config.keys():
            if "keys" in self.config[provider]:
                keys = self.config[provider]["keys"]
                if isinstance(keys, list) and keys:
                    self.key_indices[provider] = 0
                elif isinstance(keys, str) and keys.strip():
                    self.key_indices[provider] = 0

    def get_next_key(self, provider: str) -> str:
        if provider not in self.config or "keys" not in self.config[provider]:
            raise ValueError(f"Provider {provider} not found in config or has no keys")

        keys_config = self.config[provider]["keys"]

        # Handle both list and string formats
        if isinstance(keys_config, list):
            keys = keys_config
        elif isinstance(keys_config, str):
            keys = [key.strip() for key in keys_config.split(",") if key.strip()]
        else:
            raise ValueError(
                f"Keys must be a list or comma-separated string for provider {provider}"
            )

        if not keys:
            raise ValueError(f"No keys available for provider {provider}")

        current_index = self.key_indices[provider]
        key = keys[current_index]

        # Move to next key (round-robin)
        self.key_indices[provider] = (current_index + 1) % len(keys)

        return key

    def get_base_url(self, provider: str) -> str:
        if provider not in self.config or "base_url" not in self.config[provider]:
            raise ValueError(f"Base URL not found for provider {provider}")
        return self.config[provider]["base_url"]

    def get_providers(self) -> List[str]:
        providers = []
        for provider in self.config.keys():
            if "keys" in self.config[provider]:
                keys = self.config[provider]["keys"]
                if isinstance(keys, list) and keys:
                    providers.append(provider)
                elif isinstance(keys, str) and keys.strip():
                    providers.append(provider)
        return providers
