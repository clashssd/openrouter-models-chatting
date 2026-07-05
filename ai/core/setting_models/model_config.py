# ai/core/setting_models/configs/default.yaml
# imports
import yaml
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("my_app")


class ModelConfigManager:
    """Manager for model configurations, profiles, and skills"""

    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.models_dir = self.config_dir / "models"
        self.prompts_dir = self.config_dir / "prompts"
        self.skills_dir = self.config_dir / "skills"
        self.custom_models_dir = self.models_dir / "custom"
        self.custom_skills_dir = self.skills_dir / "custom"
        # Create directories if they don't exist
        for dir_path in [
            self.models_dir,
            self.prompts_dir,
            self.skills_dir,
            self.custom_models_dir,
            self.custom_skills_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

        self._default_config = None
        self._loaded_skills = {}

    # CONFIG METHODS
    def load_default_config(self) -> Dict[str, Any]:
        """Load or create default configuration"""
        default_path = self.models_dir / "default.yaml"
        if default_path.exists():
            with open(default_path, "r") as f:
                return yaml.safe_load(f)
        else:
            default_config = self._create_default_config()
            self.save_config(default_config, default_path)
            return default_config

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration structure"""
        return {
            "model": {"id": None, "name": None, "provider": None, "tier": None},
            "settings": {
                "temperature": 0.7,
                "max_tokens": 4096,
                "top_p": 0.9,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
            },
            "system_prompt": self._get_default_system_prompt(),
            "skills": [],
            "profile": {
                "name": "Default Profile",
                "description": "Default configuration for all models",
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0",
            },
        }

    def _get_default_system_prompt(self) -> str:
        """Return default system prompt"""
        return """You are a helpful AI assistant with the following characteristics:
- You provide accurate, clear, and concise responses
- You think step by step when solving complex problems
- You admit when you don't know something
- You use available tools and skills when appropriate
- You maintain a professional but approachable tone"""

    def save_config(self, config: Dict[str, Any], path: Path = None) -> bool:
        """Save configuration to YAML file"""
        try:
            if path is None:
                name = config.get("profile", {}).get("name", "default")
                path = self.custom_models_dir / f"{name.lower().replace(' ', '_')}.yaml"
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Config saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def load_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Load configuration by name or path"""
        # Check custom profiles first
        custom_path = self.custom_models_dir / f"{name}.yaml"
        if custom_path.exists():
            with open(custom_path, "r") as f:
                return yaml.safe_load(f)
        # Check default
        default_path = self.models_dir / f"{name}.yaml"
        if default_path.exists():
            with open(default_path, "r") as f:
                return yaml.safe_load(f)
        return None

    def load_model_config(self, model_id: str) -> Dict[str, Any]:
        """Load configuration for specific model"""
        # Check if there's a custom config for this model
        model_name = model_id.replace("/", "_")
        custom_path = self.custom_models_dir / f"{model_name}.yaml"
        if custom_path.exists():
            with open(custom_path, "r") as f:
                config = yaml.safe_load(f)
                config["model"]["id"] = model_id
                return config
        # Otherwise, return default config with model info filled in
        default_config = self.load_default_config()
        default_config["model"]["id"] = model_id
        default_config["model"]["name"] = (
            model_id.split("/")[-1] if "/" in model_id else model_id
        )
        default_config["model"]["provider"] = (
            model_id.split("/")[0] if "/" in model_id else "unknown"
        )
        return default_config

    def list_configs(self) -> List[str]:
        """List all available configurations"""
        configs = []
        for path in self.models_dir.glob("*.yaml"):
            if path.stem != "default":
                configs.append(path.stem)
        for path in self.custom_models_dir.glob("*.yaml"):
            configs.append(path.stem)
        return configs

    # PROFILE METHODS
    def create_profile(
        self, name: str, model_id: str, config: Dict[str, Any] = None
    ) -> bool:
        """Create a new profile for a specific model"""
        # Load base config for the model
        base_config = self.load_model_config(model_id)
        if base_config is None:
            logger.error(f"Failed to load base config for {model_id}")
            return False
        # Merge with custom config
        if config:
            for key, value in config.items():
                if isinstance(value, dict) and key in base_config:
                    base_config[key].update(value)
                else:
                    base_config[key] = value
        # Update profile info - preserve the name from config if it exists, otherwise use parameter
        if "profile" not in base_config:
            base_config["profile"] = {}
        if "name" not in base_config["profile"]:
            base_config["profile"]["name"] = name
        base_config["profile"]["created"] = time.strftime("%Y-%m-%d %H:%M:%S")
        # Save to custom profiles
        profile_path = self.custom_models_dir / f"{name}.yaml"
        return self.save_config(base_config, profile_path)

    def load_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a user profile configuration"""
        return self.load_config(name)

    def list_profiles(self) -> List[str]:
        """List all available profiles"""
        profiles = []
        for path in self.custom_models_dir.glob("*.yaml"):
            profiles.append(path.stem)
        return profiles

    def delete_profile(self, name: str) -> bool:
        """Delete a profile"""
        profile_path = self.custom_models_dir / f"{name}.yaml"
        if profile_path.exists():
            profile_path.unlink()
            logger.info(f"Profile {name} deleted")
            return True
        logger.warning(f"Profile {name} not found")
        return False

    # SKILLS METHODS
    def load_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Load a skill configuration"""
        # Check custom skills first
        custom_path = self.custom_skills_dir / f"{skill_name}.yaml"
        if custom_path.exists():
            with open(custom_path, "r") as f:
                return yaml.safe_load(f)
        # Check default skills
        skill_path = self.skills_dir / f"{skill_name}.yaml"
        if skill_path.exists():
            with open(skill_path, "r") as f:
                return yaml.safe_load(f)
        return None

    def load_skills(self, skill_names: List[str]) -> List[Dict[str, Any]]:
        """Load multiple skills"""
        skills = []
        for name in skill_names:
            skill = self.load_skill(name)
            if skill:
                skills.append(skill)
            else:
                logger.warning(f"Skill {name} not found")
        return skills

    def list_skills(self) -> List[str]:
        """List all available skills"""
        skills = []
        for path in self.skills_dir.glob("*.yaml"):
            skills.append(path.stem)
        for path in self.custom_skills_dir.glob("*.yaml"):
            skills.append(path.stem)
        return skills

    def create_skill(self, name: str, config: Dict[str, Any]) -> bool:
        """Create a custom skill"""
        if "name" not in config:
            config["name"] = name
        if "created" not in config:
            config["created"] = time.strftime("%Y-%m-%d %H:%M:%S")
        skill_path = self.custom_skills_dir / f"{name}.yaml"
        try:
            with open(skill_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Skill {name} created")
            return True
        except Exception as e:
            logger.error(f"Failed to create skill: {e}")
            return False

    def delete_skill(self, name: str) -> bool:
        """Delete a custom skill"""
        skill_path = self.custom_skills_dir / f"{name}.yaml"
        if skill_path.exists():
            skill_path.unlink()
            logger.info(f"Skill {name} deleted")
            return True
        logger.warning(f"Skill {name} not found")
        return False

    # SYSTEM PROMPT METHODS
    def get_system_prompt(self, model_id: str = None) -> str:
        """Get system prompt for model"""
        # If model_id provided, try to get from model config
        if model_id:
            config = self.load_model_config(model_id)
            if config and "system_prompt" in config:
                return config["system_prompt"]
        # Check for custom prompt file
        prompt_path = self.prompts_dir / "system_prompt.txt"
        if prompt_path.exists():
            with open(prompt_path, "r") as f:
                return f.read()
        return self._get_default_system_prompt()

    def save_system_prompt(self, prompt: str) -> bool:
        """Save custom system prompt to file"""
        prompt_path = self.prompts_dir / "system_prompt.txt"
        try:
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(prompt)
            logger.info(f"System prompt saved to {prompt_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save system prompt: {e}")
            return False

    # EXPORT/IMPORT
    def export_profile(self, name: str, path: str = None) -> bool:
        """Export profile to JSON file"""
        config = self.load_profile(name)
        if config is None:
            logger.error(f"Profile {name} not found")
            return False
        if path is None:
            path = f"{name}_export.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"Profile exported to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export profile: {e}")
            return False

    def import_profile(self, path: str) -> bool:
        """Import profile from JSON file"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)

            name = config.get("profile", {}).get("name", "imported")
            return self.create_profile(
                name, config.get("model", {}).get("id", "unknown"), config
            )
        except Exception as e:
            logger.error(f"Failed to import profile: {e}")
            return False
