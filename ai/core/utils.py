# ai/core/utils.py
# imports
import json
import time
import hashlib
import re
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import logging

# Base logger
logger = logging.getLogger("my_app")


# 1. CODE HIGHLIGHTER
class CodeHighlighter:
    """Highlight code blocks in text"""

    COLORS = {
        "keyword": "\033[1;36m",  # Cyan bold
        "string": "\033[0;32m",  # Green
        "comment": "\033[0;33m",  # Yellow
        "function": "\033[1;34m",  # Blue bold
        "class": "\033[1;35m",  # Purple bold
        "number": "\033[0;35m",  # Purple
        "operator": "\033[0;31m",  # Red
        "variable": "\033[0;33m",  # Yellow
        "builtin": "\033[1;32m",  # Green bold
        "reset": "\033[0m",
    }

    @staticmethod
    def highlight(text: str) -> str:
        pattern = r"```(\w+)?\n(.*?)```"

        def replace_code_block(match):
            lang = match.group(1) or "text"
            code = match.group(2)
            highlighted = CodeHighlighter._highlight_code(code, lang)
            return f"\n```{lang}\n{highlighted}```\n"

        return re.sub(pattern, replace_code_block, text, flags=re.DOTALL)

    @staticmethod
    def _highlight_code(code: str, lang: str) -> str:
        """Highlight code based on language"""
        if lang in ["python", "py"]:
            return CodeHighlighter._highlight_python(code)
        elif lang in ["javascript", "js"]:
            return CodeHighlighter._highlight_javascript(code)
        elif lang in ["json"]:
            return CodeHighlighter._highlight_json(code)
        elif lang in ["bash", "sh"]:
            return CodeHighlighter._highlight_bash(code)
        elif lang in ["cpp", "c++", "c"]:
            return CodeHighlighter._highlight_cpp(code)
        elif lang in ["java"]:
            return CodeHighlighter._highlight_java(code)
        elif lang in ["go"]:
            return CodeHighlighter._highlight_go(code)
        elif lang in ["rust"]:
            return CodeHighlighter._highlight_rust(code)
        else:
            return code

    @staticmethod
    def _highlight_python(code: str) -> str:
        """Highlight Python code"""
        patterns = [
            (
                r"(import|from|class|def|return|if|elif|else|for|while|try|except|finally|with|as|in|is|not|and|or|True|False|None|raise|yield|assert|pass|break|continue|lambda|del|global|nonlocal|async|await)\b",
                "keyword",
            ),
            (r"(@\w+)", "function"),
            (r'("[^"]*"|\'[^\']*\')', "string"),
            (r"(#.*$)", "comment"),
            (r"(\b\d+\.?\d*\b)", "number"),
            (r"(self|cls)\b", "variable"),
            (
                r"(\bprint|len|range|str|int|float|list|dict|set|tuple|type|open|sorted|sum|min|max|zip|enumerate|filter|map|reduce|staticmethod|classmethod|property)\b",
                "builtin",
            ),
        ]
        return CodeHighlighter._apply_patterns(code, patterns)

    @staticmethod
    def _highlight_javascript(code: str) -> str:
        """Highlight JavaScript code"""
        patterns = [
            (
                r"(const|let|var|function|return|if|else|for|while|try|catch|finally|new|this|class|extends|import|export|from|async|await|switch|case|break|continue|typeof|instanceof|yield|delete|throw)\b",
                "keyword",
            ),
            (r'("[^"]*"|\'[^\']*\'|`[^`]*`)', "string"),
            (r"(//.*$|/\*.*?\*/)", "comment"),
            (r"(\b\d+\.?\d*\b)", "number"),
            (
                r"(\bconsole|document|window|Object|Array|String|Number|Boolean|Function|Symbol|Promise|Map|Set)\b",
                "builtin",
            ),
        ]
        return CodeHighlighter._apply_patterns(code, patterns, flags=re.DOTALL)

    @staticmethod
    def _highlight_json(code: str) -> str:
        """Highlight JSON code"""
        patterns = [
            (r'("[^"]*")', "string"),
            (r"(\b\d+\.?\d*\b)", "number"),
            (r"(true|false|null)\b", "keyword"),
        ]
        return CodeHighlighter._apply_patterns(code, patterns)

    @staticmethod
    def _highlight_bash(code: str) -> str:
        """Highlight Bash code"""
        patterns = [
            (r"(#!/bin/.*$)", "comment"),
            (
                r"(echo|if|then|else|elif|fi|for|while|do|done|case|esac|function|return|source|export|unset|set|read|test|cat|grep|sed|awk|find|xargs)\b",
                "keyword",
            ),
            (r'("[^"]*"|\'[^\']*\')', "string"),
            (r"(#.*$)", "comment"),
            (r"(\b\d+\.?\d*\b)", "number"),
        ]
        return CodeHighlighter._apply_patterns(code, patterns)

    @staticmethod
    def _highlight_cpp(code: str) -> str:
        """Highlight C++ code"""
        patterns = [
            (
                r"(#include|#define|#ifndef|#endif|using|namespace|class|struct|public|private|protected|virtual|override|final|constexpr|template|typename|typedef|new|delete|this|friend|explicit|mutable|volatile|register|static|inline|virtual|operator)\b",
                "keyword",
            ),
            (r'("[^"]*"|\'[^\']*\')', "string"),
            (r"(//.*$|/\*.*?\*/)", "comment"),
            (r"(\b\d+\.?\d*\b)", "number"),
            (
                r"(\bstd|cout|cin|endl|vector|map|string|shared_ptr|unique_ptr|make_shared|make_unique)\b",
                "builtin",
            ),
        ]
        return CodeHighlighter._apply_patterns(code, patterns, flags=re.DOTALL)

    @staticmethod
    def _highlight_java(code: str) -> str:
        """Highlight Java code"""
        patterns = [
            (
                r"(public|private|protected|static|final|abstract|class|interface|enum|extends|implements|new|this|super|return|void|int|float|double|long|boolean|byte|char|short|String|System|out|println|import|package|synchronized|volatile|transient|native|strictfp|throws|try|catch|finally|throw|if|else|switch|case|break|continue|for|while|do|instanceof)\b",
                "keyword",
            ),
            (r'("[^"]*"|\'[^\']*\')', "string"),
            (r"(//.*$|/\*.*?\*/)", "comment"),
            (r"(\b\d+\.?\d*\b)", "number"),
        ]
        return CodeHighlighter._apply_patterns(code, patterns, flags=re.DOTALL)

    @staticmethod
    def _highlight_go(code: str) -> str:
        """Highlight Go code"""
        patterns = [
            (
                r"(package|import|func|type|struct|interface|map|chan|go|select|defer|return|if|else|for|range|switch|case|default|break|continue|fallthrough|goto|var|const|new|make|panic|recover|close|len|cap|append|copy|delete|complex|real|imag)\b",
                "keyword",
            ),
            (r'("[^"]*"|`[^`]*`)', "string"),
            (r"(//.*$|/\*.*?\*/)", "comment"),
            (r"(\b\d+\.?\d*\b)", "number"),
            (r"(\berr|nil|true|false|iota)\b", "builtin"),
        ]
        return CodeHighlighter._apply_patterns(code, patterns, flags=re.DOTALL)

    @staticmethod
    def _highlight_rust(code: str) -> str:
        """Highlight Rust code"""
        patterns = [
            (
                r"(fn|let|mut|pub|impl|trait|struct|enum|match|if|else|while|for|loop|return|break|continue|use|mod|crate|self|super|macro_rules|unsafe|extern|static|const|type|move|ref|where|dyn)\b",
                "keyword",
            ),
            (r'("[^"]*"|\'[^\']*\')', "string"),
            (r"(//.*$|/\*.*?\*/)", "comment"),
            (r"(\b\d+\.?\d*\b)", "number"),
            (
                r"(\bResult|Option|Some|None|Ok|Err|Vec|String|println|panic|unwrap|expect)\b",
                "builtin",
            ),
        ]
        return CodeHighlighter._apply_patterns(code, patterns, flags=re.DOTALL)

    @staticmethod
    def _apply_patterns(text: str, patterns: List[Tuple[str, str]], **kwargs) -> str:
        """Apply regex patterns with colors"""
        result = text
        for pattern, color_name in patterns:
            color = CodeHighlighter.COLORS.get(
                color_name, CodeHighlighter.COLORS["reset"]
            )
            result = re.sub(
                pattern,
                f"{color}\\g<0>{CodeHighlighter.COLORS['reset']}",
                result,
                **kwargs,
            )
        return result


# 2. PROMPT TEMPLATES
class PromptTemplates:
    """Manage prompt templates"""

    DEFAULT_TEMPLATES = {
        "code_review": {
            "description": "Review code and suggest improvements",
            "template": "Review this code and suggest improvements:\n\n```\n{{code}}\n```\n\nFocus on:\n- Code quality and readability\n- Performance issues\n- Security vulnerabilities\n- Best practices",
        },
        "explain": {
            "description": "Explain code in simple terms",
            "template": "Explain this code in simple terms:\n\n```\n{{code}}\n```\n\nExplain:\n- What it does\n- How it works\n- Why it's written this way",
        },
        "refactor": {
            "description": "Refactor code for better performance",
            "template": "Refactor this code for better performance and maintainability:\n\n```\n{{code}}\n```\n\nRequirements:\n- Keep the same functionality\n- Improve performance\n- Add comments\n- Follow best practices",
        },
        "security": {
            "description": "Security analysis of code",
            "template": "Analyze this code for security vulnerabilities:\n\n```\n{{code}}\n```\n\nCheck for:\n- Injection vulnerabilities\n- Authentication issues\n- Authorization problems\n- Data exposure\n- Security best practices",
        },
        "debug": {
            "description": "Debug code and find issues",
            "template": "Debug this code and find issues:\n\n```\n{{code}}\n```\n\nFind:\n- Syntax errors\n- Logic errors\n- Runtime issues\n- Edge cases\n- Provide fixed code",
        },
        "document": {
            "description": "Generate documentation for code",
            "template": "Generate documentation for this code:\n\n```\n{{code}}\n```\n\nInclude:\n- Description of what it does\n- Function signatures\n- Parameter descriptions\n- Return values\n- Usage examples",
        },
        "test": {
            "description": "Generate unit tests",
            "template": "Generate unit tests for this code:\n\n```\n{{code}}\n```\n\nRequirements:\n- Use appropriate testing framework\n- Cover edge cases\n- Include assertions\n- Test error conditions",
        },
    }

    def __init__(self, templates_dir: str = "configs/prompts"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load templates from file or create defaults"""
        templates_path = self.templates_dir / "templates.json"
        if templates_path.exists():
            try:
                with open(templates_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load templates: {e}")
        # Create default templates
        self._save_templates(self.DEFAULT_TEMPLATES)
        return self.DEFAULT_TEMPLATES

    def _save_templates(self, templates: Dict[str, Dict[str, str]]):
        """Save templates to file"""
        templates_path = self.templates_dir / "templates.json"
        try:
            with open(templates_path, "w") as f:
                json.dump(templates, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save templates: {e}")

    def get_template(self, name: str) -> Optional[Dict[str, str]]:
        """Get a template by name"""
        return self.templates.get(name)

    def list_templates(self) -> List[Dict[str, str]]:
        """List all available templates"""
        return [
            {"name": name, "description": data.get("description", "")}
            for name, data in self.templates.items()
        ]

    def render_template(self, name: str, **kwargs) -> Optional[str]:
        """Render a template with variables"""
        template_data = self.get_template(name)
        if not template_data:
            return None
        template = template_data.get("template", "")
        try:
            return template.replace("{{", "{").replace("}}", "}").format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return template

    def create_template(self, name: str, description: str, template: str) -> bool:
        """Create a new custom template"""
        if name in self.templates:
            logger.warning(f"Template {name} already exists")
            return False
        self.templates[name] = {"description": description, "template": template}
        self._save_templates(self.templates)
        return True

    def delete_template(self, name: str) -> bool:
        """Delete a custom template"""
        if name not in self.templates:
            return False
        if name in self.DEFAULT_TEMPLATES:
            logger.warning(f"Cannot delete default template: {name}")
            return False
        del self.templates[name]
        self._save_templates(self.templates)
        return True


# 3. TOKEN COUNTER
class TokenCounter:
    """Count tokens in text"""

    def __init__(self):
        self._encoding = None
        self._model_to_encoding = {
            "gpt-4": "cl100k_base",
            "gpt-3.5-turbo": "cl100k_base",
            "gpt-4o": "o200k_base",
            "gpt-4o-mini": "o200k_base",
            "gpt-4o-2024-05-13": "o200k_base",
            "o1": "o200k_base",
            "o1-mini": "o200k_base",
            "o3-mini": "o200k_base",
        }

    def count(self, text: str, model: str = "gpt-4") -> int:
        """Count tokens in text"""
        try:
            import tiktoken

            # Get encoding for model
            encoding_name = self._model_to_encoding.get(model, "cl100k_base")
            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(text))
        except ImportError:
            # Fallback: rough estimate (4 chars per token)
            return len(text) // 4
        except Exception as e:
            logger.warning(f"Token counting failed: {e}")
            return len(text) // 4

    def count_messages(
        self, messages: List[Dict[str, str]], model: str = "gpt-4"
    ) -> int:
        """Count tokens in a list of messages"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self.count(content, model)
        return total

    def estimate_cost(
        self, prompt_tokens: int, completion_tokens: int, model: str = "gpt-4"
    ) -> Dict[str, float]:
        """Estimate cost based on token count"""
        # Pricing per 1K tokens (in USD)
        pricing = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-4o": {"prompt": 0.005, "completion": 0.015},
            "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
        }
        price = pricing.get(model, {"prompt": 0.001, "completion": 0.002})
        return {
            "prompt_cost": (prompt_tokens / 1000) * price["prompt"],
            "completion_cost": (completion_tokens / 1000) * price["completion"],
            "total_cost": ((prompt_tokens / 1000) * price["prompt"])
            + ((completion_tokens / 1000) * price["completion"]),
        }


# 4. RESPONSE CACHE
class ResponseCache:
    """Cache responses to avoid repeated API calls"""

    def __init__(
        self,
        cache_file: str = "response_cache.json",
        max_size: int = 1000,
        ttl: int = 3600,
    ):
        self.cache_file = Path(cache_file)
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.enabled = True
        self._load()

    def _hash(self, model: str, messages: List[Dict[str, str]]) -> str:
        """Generate cache key from model and messages"""
        key_data = {"model": model, "messages": messages}
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _load(self):
        """Load cache from file"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cache entries")
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                self.cache = {}

    def _save(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _cleanup(self):
        """Remove expired and old entries"""
        now = time.time()
        expired_keys = []
        for key, data in self.cache.items():
            # Remove expired entries
            if now - data.get("timestamp", 0) > self.ttl:
                expired_keys.append(key)
            # Remove entries with None response
            elif data.get("response") is None:
                expired_keys.append(key)
        for key in expired_keys:
            del self.cache[key]
        # Limit size
        if len(self.cache) > self.max_size:
            # Sort by timestamp and remove oldest
            sorted_items = sorted(
                self.cache.items(), key=lambda x: x[1].get("timestamp", 0)
            )
            for key, _ in sorted_items[: len(self.cache) - self.max_size]:
                del self.cache[key]
        if expired_keys:
            self._save()

    def get(self, model: str, messages: List[Dict[str, str]]) -> Optional[str]:
        """Get cached response"""
        if not self.enabled:
            return None
        self._cleanup()
        key = self._hash(model, messages)
        entry = self.cache.get(key)
        if entry and entry.get("response"):
            logger.debug(f"Cache hit: {key[:8]}...")
            return entry["response"]

        return None

    def set(self, model: str, messages: List[Dict[str, str]], response: str):
        """Cache a response"""
        if not self.enabled:
            return
        key = self._hash(model, messages)
        self.cache[key] = {
            "model": model,
            "timestamp": time.time(),
            "response": response,
        }
        self._cleanup()
        self._save()

    def clear(self):
        """Clear all cache"""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Cache cleared")

    def size(self) -> int:
        """Get cache size"""
        self._cleanup()
        return len(self.cache)

    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = sum(entry.get("hits", 0) for entry in self.cache.values())
        return total / (total + self.size()) if total + self.size() > 0 else 0.0

    def toggle(self, enabled: bool = None) -> bool:
        """Toggle cache on/off"""
        if enabled is None:
            self.enabled = not self.enabled
        else:
            self.enabled = enabled
        return self.enabled


# EXPORT ALL
__all__ = ["CodeHighlighter", "PromptTemplates", "TokenCounter", "ResponseCache"]
