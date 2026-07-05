# ai/core/model_fallback.py
# imports
import time
import random
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import logging

# logger base
logger = logging.getLogger("my_app")


# class modelfallbackmanager
class ModelFallbackManager:
    """Manages automatic fallback between models on failure"""

    def __init__(self, api_checker):
        self.api_checker = api_checker
        self.fallback_history: Dict[str, List[Dict[str, Any]]] = {}
        self.blacklist: Dict[str, float] = {}  # model_id -> cooldown_until
        self.max_retries = 3
        self.cooldown_seconds = 30
        self.fallback_models = []
        # Load fallback models from config
        self._load_fallback_models()

    def _load_fallback_models(self):
        """Load fallback models from registry or config"""
        # Try to load from registry
        registry = self.api_checker.load_registry()
        if registry:
            # Get models that are marked as working
            for model in registry.get("models", []):
                if model.get("status") == "working":
                    self.fallback_models.append(model.get("id"))
        else:
            # Default fallback order (most reliable free models)
            self.fallback_models = [
                "nvidia/nemotron-3-ultra-550b-a55b:free",
                "nvidia/nemotron-3-super-120b-a12b:free",
                "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
                "liquid/lfm-2.5-1.2b-instruct:free",
                "nvidia/nemotron-3-nano-30b-a3b:free",
            ]
            logger.info(
                f"Using default fallback models: {len(self.fallback_models)} models"
            )
        # Remove current model from fallback list to avoid self-fallback
        logger.info(f"Fallback models loaded: {len(self.fallback_models)}")

    def _get_available_models(self, exclude_model: str = None) -> List[str]:
        """Get list of available models for fallback"""
        models = []
        for model_id in self.fallback_models:
            # Skip excluded model
            if exclude_model and model_id == exclude_model:
                continue
            # Skip blacklisted models
            if self._is_blacklisted(model_id):
                continue
            models.append(model_id)
        # If no models available, try to get from registry
        if not models:
            registry = self.api_checker.load_registry()
            if registry:
                for model in registry.get("models", []):
                    if model.get("status") == "working":
                        if exclude_model and model.get("id") == exclude_model:
                            continue
                        if not self._is_blacklisted(model.get("id")):
                            models.append(model.get("id"))
        return models

    def _is_blacklisted(self, model_id: str) -> bool:
        """Check if model is currently blacklisted"""
        if model_id not in self.blacklist:
            return False
        cooldown_until = self.blacklist[model_id]
        if time.time() < cooldown_until:
            return True
        # Cooldown expired, remove from blacklist
        del self.blacklist[model_id]
        return False

    def _add_to_blacklist(self, model_id: str):
        """Add model to blacklist with cooldown"""
        self.blacklist[model_id] = time.time() + self.cooldown_seconds
        logger.info(f"Model {model_id} blacklisted for {self.cooldown_seconds}s")

    def _record_failure(self, model_id: str, error: str):
        """Record a failure for a model"""
        if model_id not in self.fallback_history:
            self.fallback_history[model_id] = []
        self.fallback_history[model_id].append(
            {"timestamp": datetime.now().isoformat(), "error": error}
        )
        # Keep only last 10 failures
        if len(self.fallback_history[model_id]) > 10:
            self.fallback_history[model_id] = self.fallback_history[model_id][-10:]
        # If model failed too many times, blacklist it
        recent_failures = sum(
            1
            for f in self.fallback_history[model_id]
            if (datetime.now() - datetime.fromisoformat(f["timestamp"])).seconds < 60
        )
        if recent_failures >= 3:
            self._add_to_blacklist(model_id)
            logger.warning(f"Model {model_id} blacklisted due to frequent failures")

    def _record_success(self, model_id: str):
        """Record a successful response"""
        if model_id in self.blacklist:
            # Remove from blacklist on success
            del self.blacklist[model_id]
            logger.info(f"Model {model_id} removed from blacklist (success)")

    def get_best_model(self, exclude_model: str = None) -> Optional[str]:
        """Get the best available model for fallback"""
        available = self._get_available_models(exclude_model)
        if not available:
            logger.warning("No available models for fallback")
            return None
        # Return first available (maintained in order of preference)
        return available[0]

    def chat_with_fallback(
        self,
        primary_model: str,
        messages: list,
        config: Dict[str, Any] = None,
        max_attempts: int = 3,
        fallback_func: Callable = None,
    ) -> Optional[str]:
        models_tried = []
        models_to_try = [primary_model] + self._get_available_models(primary_model)
        # Limit attempts
        models_to_try = models_to_try[:max_attempts]
        # Determine which function to use
        if fallback_func:
            chat_func = fallback_func
        elif config:
            def chat_with_config(m, msgs):
                return self.api_checker.chat_with_config(
                    m, msgs[-1]["content"], config
                )
            chat_func = chat_with_config
        else:
            chat_func = self.api_checker.chat_completion_with_history
        for attempt, model_id in enumerate(models_to_try, 1):
            logger.info(f"Attempt {attempt}/{len(models_to_try)}: {model_id}")
            try:
                if model_id in models_tried:
                    continue
                models_tried.append(model_id)
                # Send request
                response = chat_func(model_id, messages)
                if response:
                    self._record_success(model_id)
                    logger.info(f"Success with {model_id} on attempt {attempt}")
                    return response
                else:
                    self._record_failure(model_id, "Empty response")
                    logger.warning(f"Model {model_id} returned empty response")
            except Exception as e:
                error_msg = str(e)
                self._record_failure(model_id, error_msg)
                logger.warning(f"Model {model_id} failed: {error_msg}")
                # Wait before next attempt (with jitter)
                wait_time = 0.5 * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                logger.debug(f"Waiting {wait_time:.2f}s before next attempt")
                time.sleep(wait_time)
        # All models failed
        logger.error(f"All models failed after {len(models_tried)} attempts")
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get fallback manager status"""
        return {
            "fallback_models": self.fallback_models,
            "blacklisted_models": list(self.blacklist.keys()),
            "failure_history": {
                model: len(failures)
                for model, failures in self.fallback_history.items()
            },
            "total_models": len(self.fallback_models),
        }

    def print_status(self):
        """Print fallback status"""
        status = self.get_status()
        print("\n" + "=" * 70)
        print("FALLBACK MANAGER STATUS")
        print("=" * 70)
        print(f"Total fallback models: {status['total_models']}")
        print(f"Blacklisted models: {len(status['blacklisted_models'])}")
        if status["blacklisted_models"]:
            print("\nBlacklisted:")
            for model in status["blacklisted_models"]:
                cooldown = self.blacklist.get(model, 0) - time.time()
                print(f"  {model} (cooldown: {max(0, int(cooldown))}s)")
        if status["failure_history"]:
            print("\nRecent failures:")
            for model, count in status["failure_history"].items():
                print(f"  {model}: {count} failures")
        print("=" * 70 + "\n")

    def add_fallback_model(self, model_id: str, position: int = None):
        """Add a model to fallback list"""
        if model_id not in self.fallback_models:
            if position is not None and 0 <= position < len(self.fallback_models):
                self.fallback_models.insert(position, model_id)
            else:
                self.fallback_models.append(model_id)
            logger.info(f"Added {model_id} to fallback models")

    def remove_fallback_model(self, model_id: str) -> bool:
        """Remove a model from fallback list"""
        if model_id in self.fallback_models:
            self.fallback_models.remove(model_id)
            logger.info(f"Removed {model_id} from fallback models")
            return True
        return False

    def clear_blacklist(self):
        """Clear all blacklisted models"""
        self.blacklist.clear()
        logger.info("Blacklist cleared")

    def clear_history(self):
        """Clear failure history"""
        self.fallback_history.clear()
        logger.info("Failure history cleared")


class FallbackContextManager:
    """Context manager for temporary fallback settings"""

    def __init__(self, fallback_manager: ModelFallbackManager):
        self.fallback_manager = fallback_manager
        self.original_models = None

    def __enter__(self):
        self.original_models = self.fallback_manager.fallback_models.copy()
        return self.fallback_manager

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fallback_manager.fallback_models = self.original_models
