# ai/core/setting_models/model_pinger.py
# imports
import time
import json
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger("my_app")


class ModelPinger:
    """Real-time model availability monitor"""

    def __init__(self, api_key: str, ping_interval: int = 2):
        self.api_key = api_key
        self.ping_interval = ping_interval
        self.models: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.thread = None
        self.results_file = "ping_results.json"
        # Stats tracking
        self.total_pings = 0
        self.successful_pings = 0
        self.failed_pings = 0
        # Load models from registry
        self._load_models()

    def _load_models(self):
        """Load models from registry or create new"""
        registry_path = Path("models_registry.json")
        if registry_path.exists():
            try:
                with open(registry_path, "r") as f:
                    registry = json.load(f)
                    for model in registry.get("models", []):
                        model_id = model.get("id")
                        if model_id:
                            self.models[model_id] = {
                                "name": model.get("name", model_id),
                                "status": "unknown",
                                "last_ping": None,
                                "response_time": None,
                                "uptime": 0,
                                "total_checks": 0,
                                "successful_checks": 0,
                                "provider": model.get("provider", "unknown"),
                                "tier": model.get("tier", "C"),
                                "is_free": model.get("is_free", True),
                            }
                logger.info(f"Loaded {len(self.models)} models from registry")
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
        else:
            logger.warning("No registry found, run --registry first")

    def ping_model(self, model_id: str) -> Optional[float]:
        import requests

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }
        try:
            start_time = time.time()
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            if response.status_code == 200:
                return elapsed
            else:
                logger.debug(f"Ping failed for {model_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.debug(f"Ping error for {model_id}: {e}")
            return None

    def _update_model_status(self, model_id: str, response_time: Optional[float]):
        """Update model status after ping"""
        if model_id not in self.models:
            return
        model = self.models[model_id]
        model["total_checks"] += 1
        self.total_pings += 1
        if response_time is not None:
            model["status"] = "online"
            model["last_ping"] = datetime.now().isoformat()
            model["response_time"] = round(response_time, 2)
            model["successful_checks"] += 1
            self.successful_pings += 1

            # Calculate uptime percentage
            if model["total_checks"] > 0:
                model["uptime"] = round(
                    (model["successful_checks"] / model["total_checks"]) * 100, 1
                )
        else:
            model["status"] = "offline"
            model["last_ping"] = datetime.now().isoformat()
            self.failed_pings += 1

    def _ping_loop(self):
        """Main ping loop running in separate thread"""
        logger.info(
            f"Starting ping loop with {len(self.models)} models, interval={self.ping_interval}s"
        )
        while self.running:
            start_time = time.time()
            # Ping all models
            for model_id in list(self.models.keys()):
                response_time = self.ping_model(model_id)
                self._update_model_status(model_id, response_time)
            # Save results periodically
            self._save_results()
            # Calculate sleep time to maintain interval
            elapsed = time.time() - start_time
            sleep_time = max(0, self.ping_interval - elapsed)
            time.sleep(sleep_time)

    def start(self):
        """Start the pinger in background thread"""
        if self.running:
            logger.warning("Pinger already running")
            return
        if not self.models:
            logger.error("No models loaded. Run --registry first.")
            return
        self.running = True
        self.thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.thread.start()
        logger.info("Model pinger started")

    def stop(self):
        """Stop the pinger"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self._save_results()
        logger.info("Model pinger stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of all models"""
        return {
            "total_models": len(self.models),
            "total_pings": self.total_pings,
            "successful_pings": self.successful_pings,
            "failed_pings": self.failed_pings,
            "uptime": round(
                (self.successful_pings / self.total_pings * 100)
                if self.total_pings > 0
                else 0,
                1,
            ),
            "models": self.models,
        }

    def get_online_models(self) -> List[str]:
        """Get list of online model IDs"""
        return [
            model_id
            for model_id, data in self.models.items()
            if data.get("status") == "online"
        ]

    def _save_results(self):
        """Save ping results to JSON file"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_pings": self.total_pings,
            "successful_pings": self.successful_pings,
            "failed_pings": self.failed_pings,
            "models": self.models,
        }
        try:
            with open(self.results_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

    def print_status(self):
        """Print formatted status table"""
        status = self.get_status()
        print("\n" + "=" * 80)
        print("MODEL PINGER STATUS")
        print("=" * 80)
        print(f"Total models: {status['total_models']}")
        print(f"Total pings: {status['total_pings']}")
        print(f"Successful: {status['successful_pings']}")
        print(f"Failed: {status['failed_pings']}")
        print(f"Uptime: {status['uptime']}%")
        print("=" * 80)
        # Group by status
        online = []
        offline = []
        unknown = []
        for model_id, data in status["models"].items():
            if data.get("status") == "online":
                online.append((model_id, data))
            elif data.get("status") == "offline":
                offline.append((model_id, data))
            else:
                unknown.append((model_id, data))
        # Print online models
        if online:
            print(f"\nONLINE ({len(online)})")
            print("-" * 80)
            for model_id, data in sorted(
                online, key=lambda x: x[1].get("response_time", 999)
            ):
                print(f"  {model_id}")
                print(f"    Response: {data.get('response_time', 'N/A')}ms")
                print(f"    Uptime: {data.get('uptime', 0)}%")
                print()
        # Print offline models
        if offline:
            print(f"\n❌ OFFLINE ({len(offline)})")
            print("-" * 80)
            for model_id, data in offline:
                print(f"  {model_id}")
                print(f"    Last ping: {data.get('last_ping', 'Never')}")
                print()
        # Print unknown models
        if unknown:
            print(f"\n⏳ UNKNOWN ({len(unknown)})")
            print("-" * 80)
            for model_id, data in unknown:
                print(f"  {model_id}")
                print()


def main():
    """Standalone entry point for pinger"""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    API_KEY = os.getenv("OPENROUTER_KEY")
    if not API_KEY:
        print("ERROR: OPENROUTER_KEY not found in .env")
        sys.exit(1)
    print("Starting Model Pinger...")
    print("Press Ctrl+C to stop")
    print("=" * 80)
    pinger = ModelPinger(API_KEY, ping_interval=2)
    try:
        pinger.start()
        # Display status every 10 seconds
        while True:
            time.sleep(10)
            pinger.print_status()
    except KeyboardInterrupt:
        print("\n\nStopping pinger...")
        pinger.stop()
        print("Done.")


if __name__ == "__main__":
    import sys

    sys.exit(main())
