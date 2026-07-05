# ai/core/openrouter_checker.py
# All imports
from setting_models.model_config import ModelConfigManager
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple
import os
import requests
from dotenv import load_dotenv
import logging
import logging.config
from typing import Optional, Dict, Any
import json
import time
from pathlib import Path
from model_fallback import ModelFallbackManager
from rate_limiter import RateLimiter, ModelRateLimiter
from stream_handler import StreamHandler

# Base config logging
CORE_DIR = Path(__file__).parent.absolute()
LOG_CONFIG = CORE_DIR / "logging.conf"
if LOG_CONFIG.exists():
    logging.config.fileConfig(str(LOG_CONFIG))
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    print("logging.conf not found, using default configuration")
logger = logging.getLogger("my_app")
# Import api-key from env
load_dotenv()
API_KEY = os.getenv("OPENROUTER_KEY")


# Base config OpenRouterClient
class OpenRouterClient:
    # OpenRouterClient __init__ setting
    def __init__(self, api_key: str):
        # Check api-key
        if not api_key:
            raise ValueError("API_KEY is required")
        self._api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.session = requests.Session()
        self.fallback_manager = ModelFallbackManager(self)
        self.session.headers.update(
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        self.rate_limiter = RateLimiter()
        self.model_rate_limiter = ModelRateLimiter()

    # Base get_key_info setting
    def get_key_info(self, endpoint: str, **kwargs):
        def _do_get():
            url = f"{self.base_url}/{endpoint}"
            response = self.session.get(url, timeout=30, **kwargs)
            # Update rate limit headers
            self.model_rate_limiter.update_headers(endpoint, dict(response.headers))
            if response.status_code == 429:
                raise Exception(f"Rate limit exceeded: {response.text}")
            response.raise_for_status()
            return response.json()

        try:
            return self.rate_limiter.execute_with_retry(
                func=_do_get, endpoint=endpoint, max_retries=3
            )
        except Exception as e:
            logger.error(f"GET {endpoint} failed after retries: {e}")
            return None

    # For models post
    def post_key_info(self, endpoint: str, json_data: dict, **kwargs):
        def _do_post():
            url = f"{self.base_url}/{endpoint}"
            response = self.session.post(url, json=json_data, timeout=30, **kwargs)
            # Update rate limit headers
            self.model_rate_limiter.update_headers(endpoint, dict(response.headers))
            if response.status_code == 429:
                raise Exception(f"Rate limit exceeded: {response.text}")
            response.raise_for_status()
            return response.json()

        try:
            return self.rate_limiter.execute_with_retry(
                func=_do_post, endpoint=endpoint, max_retries=3
            )
        except Exception as e:
            logger.error(f"POST {endpoint} failed after retries: {e}")
            return None

    def _extract_provider(self, model_id: str) -> str:
        # Name of providers and ID
        if "/" in model_id:
            return model_id.split("/")[0]
        return "unknown"

    def _determine_tier(self, model: dict) -> str:
        benchmarks = model.get("benchmarks", {})

        # 1. SWE-bench
        swe_bench = benchmarks.get("swe_bench")
        if swe_bench is not None:
            if swe_bench >= 70:
                return "S+"
            elif swe_bench >= 60:
                return "S"
            elif swe_bench >= 50:
                return "A+"
            elif swe_bench >= 40:
                return "A"
            elif swe_bench >= 30:
                return "B+"
            else:
                return "B"

        # 2. Artificial Analysis (исправлено)
        aa_data = benchmarks.get("artificial_analysis", {})
        if aa_data:
            scores = []
            for key in ["intelligence_index", "coding_index", "agentic_index"]:
                value = aa_data.get(key)
                if value is not None:
                    scores.append(value)

            if scores:
                avg_score = sum(scores) / len(scores)
                if avg_score >= 70:
                    return "S"
                elif avg_score >= 60:
                    return "A+"
                elif avg_score >= 50:
                    return "A"
                elif avg_score >= 40:
                    return "B+"
                else:
                    return "B"

        # 3. Design Arena ELO
        da_data = benchmarks.get("design_arena", [])
        if da_data:
            elos = [item["elo"] for item in da_data if item.get("elo") is not None]
            if elos:
                avg_elo = sum(elos) / len(elos)
                if avg_elo >= 1350:
                    return "S"
                elif avg_elo >= 1250:
                    return "A+"
                elif avg_elo >= 1150:
                    return "A"
                elif avg_elo >= 1050:
                    return "B+"
                else:
                    return "B"

        # 4. Определение по цене
        pricing = model.get("pricing", {})
        is_free = pricing.get("prompt", 1) == 0 and pricing.get("completion", 1) == 0
        return "B" if is_free else "B+"

    # Parser models  metadata
    def _parse_model_metadata(self, model: dict) -> Dict[str, Any]:
        model_id = model.get("id", "unknown")
        pricing = model.get("pricing", {})
        is_free = pricing.get("prompt", 1) == 0 and pricing.get("completion", 1) == 0
        return {
            "id": model_id,
            "name": model.get("name", model_id),
            "provider": self._extract_provider(model_id),
            "tier": self._determine_tier(model),
            "context_length": model.get("context_length", "N/A"),
            "is_free": is_free,
            "pricing": pricing,
            "status": "unknown",
        }

    def load_registry(
        self, filename: str = "models_registry.json"
    ) -> Optional[Dict[str, Any]]:
        """Load model registry from file"""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Registry file {filename} not found")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing registry: {e}")
            return None


# ApiKeyChecker on base OpenRouterClient
class ApiKeyChecker(OpenRouterClient):
    # Base ApiKeyChecker __init__ setting
    def __init__(self, api_key):
        super().__init__(api_key)
        self.models_cache_file = "models_cache.json"
        self._models_cache = None
        self.config_manager = ModelConfigManager()
        self.fallback_manager = ModelFallbackManager(self)
        self.stream_handler = StreamHandler(self)
        # Endpoints checker

    def chat_with_config(
        self, model_id: str, user_message: str, profile: str = None
    ) -> Optional[str]:
        """Chat with model using configuration"""
        if profile:
            config = self.config_manager.load_profile(profile)
        else:
            config = self.config_manager.load_model_config(model_id)
        if config is None:
            logger.error(f"No configuration found for {model_id}")
            return None
        # Build messages
        messages = []
        # Add system prompt if present
        system_prompt = config.get("system_prompt")
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        # Add user message
        messages.append({"role": "user", "content": user_message})
        # Build payload with settings
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": config.get("settings", {}).get("temperature", 0.7),
            "max_tokens": config.get("settings", {}).get("max_tokens", 4096),
            "top_p": config.get("settings", {}).get("top_p", 0.9),
        }
        response = self.post_key_info("chat/completions", payload)
        if response is None:
            return None
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            logger.error(f"Unexpected response format from {model_id}")
            return None

    # Status check
    def get_key_status(self) -> Optional[Dict[str, Any]]:
        # Check api-key status
        data = self.get_key_info("key")
        # if data is empty logging error
        if data is None:
            logger.error("Failed to get API key status")
            return None
        # parse important
        logger.info(f"API key check successful: {data.get('label', 'Unknown')}")
        return {
            "label": data.get("label", "N/A"),
            "limit": data.get("limit", None),
            "usage": data.get("usage", 0),
            "is_free_tier": data.get("is_free_tier", True),
            "rate_limit": data.get("rate_limit", {}).get("requests", "N/A"),
            "raw_data": data,
        }

    # Get list with all models
    def get_all_models(self) -> Optional[list]:
        # Check status before check models
        data = self.get_key_status()
        if data is None:
            return None
        elif data.get("limit") is not None:
            logger.warning("API key has limit, but that's normal")
        elif not data.get("is_free_tier", True):
            logger.warning("API key is not on free tier")
            return None
        # If we have cache return
        if self._models_cache is not None:
            return self._models_cache
        data = self.get_key_info("models")
        if data is None:
            return None
        # Write cache in models_cache
        self._models_cache = data.get("data", [])
        return self._models_cache

    # Get only free models
    def get_free_models(self) -> list:
        models = self.get_all_models()
        if models is None:
            return []
        free_models = []
        for model in models:
            # Check id
            if model.get("id", "").endswith(":free"):
                free_models.append(model)
        return free_models

    def save_all_models(
        self, models: list, filename: str = "models_registry.json"
    ) -> None:
        # Save all models
        registry = {
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_models": len(models),
            "models": [],
        }
        for model in models:
            parsed = self._parse_model_metadata(model)
            registry["models"].append(parsed)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(registry['models'])} models to {filename}")

    def load_registry(
        self, filename: str = "models_registry.json"
    ) -> Optional[Dict[str, Any]]:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Registry file {filename} not found")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing registry: {e}")
            return None

    def update_registry_status(
        self, results: Dict[str, Any], filename: str = "models_registry.json"
    ) -> bool:
        registry = self.load_registry(filename)
        if registry is None:
            logger.error("Registry not found, cannot update status")
            return False
        updated = 0
        for model in registry.get("models", []):
            model_id = model.get("id")
            if model_id in results:
                status = results[model_id].get("status", "unknown")
                if status in ["OK", "OK"]:
                    model["status"] = "working"
                elif status in ["FAIL", "ERROR", "TIMEOUT/ERROR"]:
                    model["status"] = "failed"
                else:
                    model["status"] = "unknown"
                updated += 1
        registry["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

        logger.info(f"Updated status for {updated} models in {filename}")
        return True

    def get_models_by_tier(self, registry: Dict[str, Any]) -> Dict[str, list]:
        tiers = ["S+", "S", "A+", "A", "B+", "B", "C"]
        grouped = {tier: [] for tier in tiers}

        for model in registry.get("models", []):
            tier = model.get("tier", "C")
            if tier not in grouped:
                grouped[tier] = []
            grouped[tier].append(model)

        return grouped

    def select_model_interactive(self, registry: Dict[str, Any]) -> Optional[str]:
        grouped = self.get_models_by_tier(registry)
        tiers = ["S+", "S", "A+", "A", "B+", "B", "C"]
        print("\n" + "=" * 70)
        print("Accessible models (group in tiers)")
        print("=" * 70)
        # Collectings all models
        all_models = []
        for tier in tiers:
            models = grouped.get(tier, [])
            if models:
                print(f"\n {tier} ({len(models)} models)")
                print("-" * 40)
                for i, model in enumerate(models, 1):
                    model_id = model.get("id", "unknown")
                    name = model.get("name", model_id)
                    is_free = model.get("is_free", True)
                    context = model.get("context_length", "N/A")
                    print(f"  [{i}] {model_id}")
                    print(f"       {name}")
                    print(f"     Context: {context}")
                    if not is_free:
                        pricing = model.get("pricing", {})
                        print(
                            f"       Price: {pricing.get('prompt', '?')}/{pricing.get('completion', '?')}"
                        )
                    print()

                    all_models.append(model_id)
        print("=" * 70)
        while True:
            try:
                choice = input("\n🔢 Enter the number or ID (q - exit): ").strip()
                if choice.lower() == "q":
                    return None

                # Checking on number
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(all_models):
                        return all_models[idx]
                    else:
                        print(f"Number {choice} not in (1-{len(all_models)})")
                        continue
                # Проверяем, не ID ли это
                if choice in all_models:
                    return choice
                print(f"Model '{choice}' not found")
            except KeyboardInterrupt:
                print("\n\nExiting..")
                return None
            except Exception as e:
                print(f"Error: {e}")

    # Post for models
    def chat_completion(self, model: str, prompt: str) -> Optional[str]:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 10,
        }
        response = self.post_key_info("chat/completions", payload)
        if response is None:
            return None
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            logger.error(f"Unexpected response format from {model}")
            return None

    # Check all free models asynchronously
    def check_free_models(
        self, prompt="Hey, write for me 1 word", max_workers=5
    ) -> Dict[str, Any]:
        free_models = self.get_free_models()
        if not free_models:
            logger.warning("No free models found")
            return {}
        results = {}
        total = len(free_models)
        logger.info(
            f"Starting async check of {total} free models with {max_workers} workers"
        )

        def _test_model(model: dict) -> Tuple[str, dict]:
            model_id = model.get("id")
            try:
                response = self.chat_completion(model_id, prompt)
                return model_id, {
                    "name": model.get("name", model_id),
                    "status": "OK" if response else "FAIL",
                    "response": response[:50] if response else None,
                }
            except Exception as e:
                logger.error(f"Error testing {model_id}: {e}")
                return model_id, {
                    "name": model.get("name", model_id),
                    "status": "ERROR",
                    "response": None,
                }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_model = {
                executor.submit(_test_model, model): model for model in free_models
            }
            completed = 0
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                model_id = model.get("id")
                try:
                    result_id, result_data = future.result(timeout=45)
                    results[result_id] = result_data
                    completed += 1
                    logger.info(
                        f"[{completed}/{total}] {result_id} - {result_data['status']}"
                    )
                except Exception as e:
                    logger.error(f"Unexpected error for {model_id}: {e}")
                    results[model_id] = {
                        "name": model.get("name", model_id),
                        "status": "TIMEOUT/ERROR",
                        "response": None,
                    }
        return results

    # Get from model all history
    def chat_completion_with_history(self, model: str, messages: list) -> Optional[str]:
        payload = {"model": model, "messages": messages, "max_tokens": 500}
        response = self.post_key_info("chat/completions", payload)
        if response is None:
            return None
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            logger.error(f"Unexpected response format from {model}")
            return None

    # Save results in json
    def save_results(self, results: Dict[str, Any], filename: str = None) -> None:
        if filename is None:
            filename = f"models_check_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {filename}")

    # Saving working models in file
    def save_working_models(
        self, results: Dict[str, Any], filename: str = None
    ) -> None:
        working = {
            model_id: data
            for model_id, data in results.items()
            if data.get("status") == "OK"
        }
        if not working:
            logger.warning("No working models found to save")
            return
        if filename is None:
            filename = "working_models.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(working, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(working)} working models to {filename}")


if __name__ == "__main__":
    print("=" * 70)
    print("OpenRouter Model Checker v2.0")
    print("=" * 70)

    # Validate API key
    if not API_KEY:
        print("ERROR: API_KEY not found in .env file")
        print("Create .env with: OPENROUTER_KEY=sk-or-v1-xxx")
        exit(1)

    checker = ApiKeyChecker(API_KEY)

    # 1. Check API key status
    print("\n[1/4] Checking API key...")
    key_status = checker.get_key_status()
    if key_status is None:
        print("ERROR: Invalid API key")
        exit(1)

    print(f"Key: {key_status['label']}")
    print(f"Free Tier: {'Yes' if key_status['is_free_tier'] else 'No'}")
    print(f"Usage: {key_status['usage']} credits")
    print(f"Rate Limit: {key_status['rate_limit']} req/sec")

    # 2. Fetch all models
    print("\n[2/4] Loading models...")
    all_models = checker.get_all_models()
    if all_models is None:
        print("ERROR: Failed to load models")
        exit(1)

    free_models = [m for m in all_models if m.get("id", "").endswith(":free")]
    paid_models = [m for m in all_models if not m.get("id", "").endswith(":free")]

    print(f"Total models: {len(all_models)}")
    print(f"Free models: {len(free_models)}")
    print(f"Paid models: {len(paid_models)}")

    # 3. Save registry
    print("\n[3/4] Saving registry...")
    checker.save_all_models(all_models)
    print("Registry saved to models_registry.json")

    # 4. Check free models (async)
    print("\n[4/4] Checking free models (async)...")
    print("This may take 30-60 seconds...")

    results = checker.check_free_models(max_workers=5)

    # Statistics
    total = len(results)
    working = [m for m, r in results.items() if r["status"] == "OK"]
    failed = [m for m, r in results.items() if r["status"] != "OK"]

    print("\n" + "=" * 70)
    print("CHECK RESULTS")
    print("=" * 70)
    print(f"Models checked: {total}")
    print(f"Working: {len(working)}")
    print(f"Failed: {len(failed)}")
    print(f"Success rate: {len(working)/total*100:.1f}%")

    # Save results
    if results:
        checker.save_results(results)
        checker.save_working_models(results)
        checker.update_registry_status(results)
        print("Results saved:")
        print("  - models_check_*.json (all models)")
        print("  - working_models.json (working only)")
        print("  - models_registry.json (updated registry)")

    # Show working models
    if working:
        print("\n" + "=" * 70)
        print("WORKING MODELS")
        print("=" * 70)
        for i, (model_id, data) in enumerate(results.items(), 1):
            if data["status"] == "OK":
                print(f"{i:2}. {model_id}")
                print(f"    Name: {data.get('name', 'N/A')}")
                if data.get("response"):
                    print(f"    Response: {data['response'][:80]}...")
                print()
    else:
        print("\nNo working models found. All may be overloaded.")

    # Interactive model selection
    print("\n" + "=" * 70)
    print("INTERACTIVE MODEL SELECTION")
    print("=" * 70)

    registry = checker.load_registry()
    if registry:
        selected = checker.select_model_interactive(registry)
        if selected:
            print(f"\nSelected model: {selected}")

            # Test query
            print("\nSending test query...")
            test_response = checker.chat_completion(selected, "Hello! Write one word.")
            if test_response:
                print(f"Response: {test_response[:100]}...")
            else:
                print("ERROR: Model did not respond")
        else:
            print("Selection cancelled")
    else:
        print("ERROR: Registry not found")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
    print("\nAvailable commands:")
    print("  python main.py --check      # Check models")
    print("  python main.py --list       # Show working models")
    print("  python main.py --select     # Interactive selection")
    print("  python main.py --help       # Help")
