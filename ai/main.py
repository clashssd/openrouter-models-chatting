# ai/main.py
# imports
import argparse
import sys
import os
from typing import Dict, Any
import time

# Path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))
try:
    from openrouter_checker import ApiKeyChecker, API_KEY
    from ai.core.setting_models import ModelConfigManager
    from chat_handler import ChatManager, ChatSession
except ImportError as e:
    print(f"Import error: {e}")
    print(
        "Ensure that the file core/openrouter_checker.py exists and contains the ApiKeyChecker class."
    )
    sys.exit(1)


# conf colors
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


# banner
def print_banner():
    banner = f"""
{Colors.RED}{Colors.BOLD}
⠀⠀⠀⠀⠀⠀ ⢀⣤⣤⣤⣄⣀⣠⣤⣤⣄⡀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣰⠟⠁⠀⠀⠀⠉⠉⠀⠀⠀⠈⠛⢷⡄⠀⠀⠀⠀⠀
⠀⠀⢀⣴⠾⠃⠀⠀⣾⣿⣷⡄⠀⢠⣾⣿⣷⡄⠈⣿⣤⣄⡀⠀⠀
⠀⢰⡟⠁⠀⣀⡀⠘⣿⣿⣿⡇⠀⢸⣿⣿⣿⠃⠀⠀⠀⠈⢻⣆⠀
⠀⣿⡇⠀⣼⣿⣿⡄⠈⠛⠛⠁⠀⠀⠙⠉⠁⠀⣠⣶⣦⡀⠀⣿⠀
⠀⣿⡇⠀⠸⣿⣿⠇⠀⠀⣠⣾⣿⣿⣦⠀⠀⢸⣿⣿⣿⠇⠀⣿⠀❤ OpenRouter Model Checker ❤
⠀⢸⣇⠀⠀⠈⠁⠀⣠⣶⣿⣿⣿⣿⣿⣧⣄⠈⠛⠛⠋⠀⣼⠃⠀❤ by CLASHSSD ❤
⠀⠀⢿⡄⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⣼⡏⠀⠀
⠀⠀⠈⣿⡀⠀⠀⠈⠻⠿⠟⠛⠛⠻⠿⠿⠟⠃⠀⠀⢸⣿⠀⠀⠀
⠀⠀⠀ ⣽⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ⢸⡟⠀⠀⠀
⠀ ⠀⠀⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇{Colors.END}

{Colors.CYAN}{Colors.BOLD}         OpenRouter Model Checker {Colors.END}
{Colors.DIM}         Checking availability of free models{Colors.END}

{Colors.DIM}[*] https://openrouter.ai | https://github.com/clashssd{Colors.END}

{Colors.GREEN}    +---[API Status]---+
    |  {Colors.CYAN}Target: OpenRouter API{Colors.GREEN}  |
    |  {Colors.CYAN}Status: Ready{Colors.GREEN}           |
    +------------------+

{Colors.END}"""
    print(banner)


# functions for uotput
def print_header(text: str, color: str = Colors.CYAN):
    print(f"\n{color}{Colors.BOLD}[+] {text}{Colors.END}")


def print_success(text: str):
    print(f"{Colors.GREEN}[+] {text}{Colors.END}")


def print_error(text: str):
    print(f"{Colors.RED}[-] {text}{Colors.END}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}[!] {text}{Colors.END}")


def print_info(text: str):
    print(f"{Colors.BLUE}[*] {text}{Colors.END}")


def print_debug(text: str):
    print(f"{Colors.DIM}[.] {text}{Colors.END}")


def print_key_value(key: str, value: str, color: str = Colors.CYAN):
    print(f"{Colors.DIM}  |{Colors.END} {color}{key}:{Colors.END} {value}")


def print_table(results: Dict[str, Any]) -> None:
    if not results:
        print_warning("No results")
        return
    total = len(results)
    working = [r for r in results.values() if r.get("status") == "OK"]
    print_header("Verification statistics", Colors.BLUE)
    print(f"{Colors.DIM}  +{'-' * 40}+{Colors.END}")
    print_key_value("Total models", str(total))
    print_key_value(
        "Working", f"{Colors.GREEN}{len(working)}{Colors.END}", Colors.GREEN
    )
    print_key_value(
        "Not working", f"{Colors.RED}{total - len(working)}{Colors.END}", Colors.RED
    )
    print(f"{Colors.DIM}  +{'-' * 40}+{Colors.END}")
    if working:
        print_header("Working models found", Colors.GREEN)
        print(f"{Colors.DIM}  +{'-' * 60}+{Colors.END}")
        for i, (model_id, data) in enumerate(results.items(), 1):
            if data.get("status") == "OK":
                print(
                    f"  {Colors.DIM}|{Colors.END} {Colors.GREEN}{i:2}. ✅{Colors.END} {Colors.CYAN}{model_id}{Colors.END}"
                )
                if data.get("response"):
                    print(
                        f"  {Colors.DIM}|{Colors.END}    {Colors.DIM}└─ 💬{Colors.END} {data['response'][:60]}..."
                    )
        print(f"{Colors.DIM}  +{'-' * 60}+{Colors.END}")
    failed = [r for r in results.values() if r.get("status") != "OK"]
    if failed:
        print_header("Unavailable models", Colors.RED)
        print(f"{Colors.DIM}  +{'-' * 60}+{Colors.END}")
        for i, (model_id, data) in enumerate(results.items(), 1):
            if data.get("status") != "OK":
                status_text = data.get("status", "UNKNOWN")
                print(
                    f"  {Colors.DIM}|{Colors.END} {Colors.RED}{i:2}. ❌{Colors.END} {Colors.YELLOW}{model_id}{Colors.END}"
                )
                print(
                    f"  {Colors.DIM}|{Colors.END}    {Colors.DIM}└─ Status:{Colors.END} {Colors.RED}{status_text}{Colors.END}"
                )
        print(f"{Colors.DIM}  +{'-' * 60}+{Colors.END}")


def cmd_list_configs() -> int:
    """List all configurations"""
    print_header("Configurations", Colors.BLUE)
    manager = ModelConfigManager()
    configs = manager.list_configs()
    if not configs:
        print_warning("No configurations found")
        return 0
    for config in configs:
        print(f"  {Colors.CYAN}{config}{Colors.END}")
    return 0


def cmd_list_profiles() -> int:
    """List all profiles"""
    print_header("Profiles", Colors.PURPLE)
    manager = ModelConfigManager()
    profiles = manager.list_profiles()
    if not profiles:
        print_warning("No profiles found")
        print_info("Create one with: --create-profile NAME")
        return 0
    for profile in profiles:
        print(f"  {Colors.GREEN}{profile}{Colors.END}")
    return 0


def cmd_list_skills() -> int:
    """List all skills"""
    print_header("Skills", Colors.CYAN)
    manager = ModelConfigManager()
    skills = manager.list_skills()
    if not skills:
        print_warning("No skills found")
        return 0
    for skill in skills:
        print(f"  {Colors.YELLOW}{skill}{Colors.END}")
    return 0


def cmd_create_profile(args) -> int:
    """Create a new profile"""
    print_header(f"Creating profile: {args.create_profile}", Colors.GREEN)
    manager = ModelConfigManager()
    # Get model ID from user
    model_id = input(
        "Enter model ID (e.g., nvidia/nemotron-3-ultra-550b-a55b:free): "
    ).strip()
    if not model_id:
        print_error("Model ID is required")
        return 1
    # Create profile
    config = {
        "settings": {"temperature": 0.7, "max_tokens": 4096},
        "system_prompt": "You are a helpful AI assistant.",
    }
    if manager.create_profile(args.create_profile, model_id, config):
        print_success(f"Profile '{args.create_profile}' created for {model_id}")
        return 0
    else:
        print_error("Failed to create profile")
        return 1


def cmd_show_config(args) -> int:
    """Show configuration"""
    print_header(f"Configuration: {args.show_config}", Colors.BLUE)
    manager = ModelConfigManager()
    config = manager.load_config(args.show_config)
    if config is None:
        print_error(f"Config '{args.show_config}' not found")
        return 1
    import json

    print(json.dumps(config, indent=2, ensure_ascii=False))
    return 0


def cmd_create_registry(checker: ApiKeyChecker) -> int:
    """Create registry of all models"""
    print_header("Creating model registry", Colors.PURPLE)
    models = checker.get_all_models()
    if models is None:
        print_error("Failed to get models")
        return 1
    checker.save_all_models(models)
    print_success(f"Saved {len(models)} models to models_registry.json")
    return 0


def cmd_select(checker: ApiKeyChecker) -> int:
    """Interactive model selection from registry"""
    print_header("Model selection", Colors.PURPLE)
    registry = checker.load_registry()
    if registry is None:
        print_warning("Registry not found. Creating new one...")
        models = checker.get_all_models()
        if models is None:
            print_error("Failed to load models")
            return 1
        checker.save_all_models(models)
        registry = checker.load_registry()
        if registry is None:
            print_error("Failed to load registry")
            return 1
    selected = checker.select_model_interactive(registry)
    if selected is None:
        print_info("Selection cancelled")
        return 0
    print_success(f"Selected model: {selected}")
    return 0


def cmd_list_sessions() -> int:
    """List all chat sessions"""
    print_header("Chat Sessions", Colors.BLUE)
    manager = ChatManager()
    sessions = manager.list_sessions()
    if not sessions:
        print_warning("No sessions found")
        return 0
    for session in sessions:
        print(f"  {Colors.CYAN}{session['id']}{Colors.END}")
        print(f"    Model: {session['model_id']}")
        print(f"    Messages: {session['message_count']}")
        print(f"    Updated: {session['updated_at']}")
        print()
    return 0


def cmd_load_session(checker: ApiKeyChecker, session_id: str) -> int:
    """Load a previous chat session"""
    manager = ChatManager()
    session = manager.get_session(session_id)
    if session is None:
        print_error(f"Session {session_id} not found")
        return 1
    print_success(f"Loaded session: {session_id}")
    return cmd_chat(checker, session.model_id, session.profile)


def cmd_chat(checker: ApiKeyChecker, model_id: str, profile: str = None) -> int:
    """Open interactive chat with a model"""
    print_header(f"Chat with: {model_id}", Colors.GREEN)
    # Load profile if specified
    config = None
    if profile:
        config = checker.config_manager.load_profile(profile)
        if config is None:
            print_warning(f"Profile '{profile}' not found, using default")
        else:
            print_info(f"Using profile: {profile}")
    # Create chat manager with stream handler
    chat_manager = ChatManager(
        fallback_manager=checker.fallback_manager, stream_handler=checker.stream_handler
    )
    # Create streaming session
    session_id = chat_manager.create_streaming_session(model_id, profile, config)
    streaming_session = chat_manager.current_session.streaming_session
    print_info(f"Session ID: {session_id}")
    print_info("Commands: /help, /clear, /model, /profile, /export, /stream, /exit")
    print("=" * 70)
    # Chat loop
    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue
            # Handle commands
            if user_input.startswith("/"):
                if user_input in ["/exit", "/quit"]:
                    print_info("Goodbye!")
                    break
                elif user_input == "/clear":
                    chat_manager.clear_session(session_id)
                    if streaming_session:
                        streaming_session.clear()
                    print_info("History cleared")
                    continue
                elif user_input == "/stream":
                    if streaming_session:
                        streaming_session.toggle_streaming()
                    else:
                        print_warning("Streaming not available")
                    continue
                elif user_input == "/help":
                    _print_chat_help()
                    continue
                elif user_input == "/stats":
                    _print_stats(chat_manager.current_session)
                    continue
                elif user_input.startswith("/model"):
                    parts = user_input.split()
                    if len(parts) > 1:
                        new_model = parts[1]
                        # Update streaming session
                        if streaming_session:
                            streaming_session.model = new_model
                            streaming_session.clear()
                        # Update chat session
                        chat_manager.current_session.model_id = new_model
                        chat_manager.current_session.clear()
                        print_success(f"Switched to model: {new_model}")
                    else:
                        print_warning("Usage: /model MODEL_ID")
                    continue
                elif user_input.startswith("/profile"):
                    parts = user_input.split()
                    if len(parts) > 1:
                        new_profile = parts[1]
                        config = checker.config_manager.load_profile(new_profile)
                        if config:
                            chat_manager.current_session.profile = new_profile
                            chat_manager.current_session.config = config
                            chat_manager.current_session.clear()
                            if streaming_session:
                                streaming_session.clear()
                            print_success(f"Switched to profile: {new_profile}")
                        else:
                            print_error(f"Profile '{new_profile}' not found")
                    else:
                        print_warning("Usage: /profile NAME")
                    continue
                elif user_input.startswith("/export"):
                    parts = user_input.split()
                    fmt = parts[1] if len(parts) > 1 else "markdown"
                    exported = chat_manager.export_session(session_id, fmt)
                    if exported:
                        filename = f"chat_export_{session_id}.{fmt}"
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(exported)
                        print_success(f"Exported to: {filename}")
                    else:
                        print_error("Export failed")
                    continue
                else:
                    print_warning(
                        f"Unknown command: {user_input}. Type /help for commands."
                    )
                    continue
            # Send message with streaming
            if streaming_session:
                # Use streaming
                response = streaming_session.send_message(user_input, streaming=True)
                if not response:
                    print_error("Model did not respond")
            else:
                # Fallback to non-streaming
                print("AI: ", end="", flush=True)
                response = checker.chat_completion_with_history(
                    model_id,
                    chat_manager.current_session.messages
                    + [{"role": "user", "content": user_input}],
                )
                if response:
                    print(response)
                    chat_manager.add_message(session_id, "assistant", response)
                else:
                    print("[ERROR: Model did not respond]")
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print_error(f"Error: {e}")
    return 0


def _print_chat_help():
    """Print chat help"""
    help_text = f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║                    CHAT COMMANDS                          ║
╚══════════════════════════════════════════════════════════╝{Colors.END}
{Colors.GREEN}/help{Colors.END}          Show this help
{Colors.GREEN}/clear{Colors.END}         Clear chat history
{Colors.GREEN}/model ID{Colors.END}      Switch to different model
{Colors.GREEN}/profile NAME{Colors.END}  Switch to different profile
{Colors.GREEN}/stream{Colors.END}        Toggle streaming on/off
{Colors.GREEN}/stats{Colors.END}         Show session statistics
{Colors.GREEN}/export{Colors.END}        Export chat (markdown, json, text)
{Colors.GREEN}/exit{Colors.END}          Exit chat
{Colors.DIM}Example:{Colors.END}
  {Colors.CYAN}/model nvidia/nemotron-3-ultra-550b-a55b:free{Colors.END}
  {Colors.CYAN}/profile my_coding_profile{Colors.END}
"""
    print(help_text)


def cmd_ping() -> int:
    """Start real-time model pinger"""
    from core.setting_models.model_pinger import ModelPinger

    print_header("Starting Model Pinger", Colors.PURPLE)
    print_info("Press Ctrl+C to stop")
    if not API_KEY:
        print_error("API_KEY not found")
        return 1
    pinger = ModelPinger(API_KEY, ping_interval=2)
    try:
        pinger.start()
        # Display status every 10 seconds
        while True:
            time.sleep(10)
            print_table(pinger.get_status())
    except KeyboardInterrupt:
        print("\n")
        print_warning("Stopping pinger...")
        pinger.stop()
        print_success("Pinger stopped")

    return 0


def cmd_fallback_status(checker: ApiKeyChecker) -> int:
    """Show fallback manager status"""
    checker.fallback_manager.print_status()
    return 0


def cmd_clear_blacklist(checker: ApiKeyChecker) -> int:
    """Clear blacklisted models"""
    checker.fallback_manager.clear_blacklist()
    print_success("Blacklist cleared")
    return 0


def cmd_add_fallback(checker: ApiKeyChecker, model_id: str) -> int:
    """Add model to fallback list"""
    checker.fallback_manager.add_fallback_model(model_id)
    print_success(f"Added {model_id} to fallback list")
    return 0


def cmd_remove_fallback(checker: ApiKeyChecker, model_id: str) -> int:
    """Remove model from fallback list"""
    if checker.fallback_manager.remove_fallback_model(model_id):
        print_success(f"Removed {model_id} from fallback list")
        return 0
    else:
        print_error(f"Model {model_id} not in fallback list")
        return 1


def cmd_rate_status(checker: ApiKeyChecker) -> int:
    """Show rate limit status"""
    print_header("Rate Limit Status", Colors.BLUE)
    limits = checker.model_rate_limiter.get_limits()
    print("Global limits:")
    print(f"  Limit: {limits.get('limit', 'N/A')}")
    print(f"  Remaining: {limits.get('remaining', 'N/A')}")
    print(f"  Reset: {limits.get('reset', 'N/A')}")
    # Check if we have active backoffs
    if checker.rate_limiter.backoff_times:
        print("\nActive backoffs:")
        for endpoint, until in checker.rate_limiter.backoff_times.items():
            remaining = max(0, until - time.time())
            print(f"  {endpoint}: {remaining:.1f}s remaining")
    return 0


def cmd_reset_rate(checker: ApiKeyChecker) -> int:
    """Reset rate limiter state"""
    checker.rate_limiter.reset()
    checker.model_rate_limiter.reset()
    print_success("Rate limiter reset")
    return 0


def cmd_templates() -> int:
    """List available prompt templates"""
    print_header("Prompt Templates", Colors.BLUE)
    templates = PromptTemplates()

    for t in templates.list_templates():
        print(f"  {Colors.CYAN}{t['name']}{Colors.END}")
        print(f"    {t['description']}")
        print()

    return 0


def cmd_render_template(name: str) -> int:
    """Render a prompt template"""
    print_header(f"Template: {name}", Colors.BLUE)
    templates = PromptTemplates()

    template = templates.get_template(name)
    if not template:
        print_error(f"Template '{name}' not found")
        return 1

    print(f"Description: {template.get('description', 'N/A')}")
    print("\n" + "=" * 70)
    print(template.get("template", ""))
    print("=" * 70)

    return 0


def cmd_cache_status() -> int:
    """Show cache status"""
    print_header("Cache Status", Colors.BLUE)
    cache = ResponseCache()
    print(f"Enabled: {cache.enabled}")
    print(f"Size: {cache.size()} entries")
    print(f"Hit rate: {cache.hit_rate():.1f}%")
    return 0


def cmd_clear_cache() -> int:
    """Clear response cache"""
    cache = ResponseCache()
    cache.clear()
    print_success("Cache cleared")
    return 0


# Main functions
def main():
    parser = argparse.ArgumentParser(
        description="OpenRouter Model Checker — Checking model availability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{Colors.CYAN}{Colors.BOLD}Usage examples:{Colors.END}

  {Colors.GREEN}python main.py --check{Colors.END}              Check all models
  {Colors.GREEN}python main.py --list{Colors.END}               Show working models from the cache
  {Colors.GREEN}python main.py --test MODEL_ID{Colors.END}      Check a specific model
  {Colors.GREEN}python main.py --api-key{Colors.END}            Show API key status
  {Colors.GREEN}python main.py --models{Colors.END}             Show all available models
  {Colors.GREEN}python main.py --help{Colors.END}               Show help

{Colors.DIM}[+] Options: --workers N   Number of threads (default: 5){Colors.END}
        """,
    )
    # Command-line arguments
    parser.add_argument(
        "--templates", action="store_true", help="List available prompt templates"
    )
    parser.add_argument(
        "--render-template", metavar="NAME", type=str, help="Render a prompt template"
    )
    parser.add_argument("--cache-status", action="store_true", help="Show cache status")
    parser.add_argument(
        "--clear-cache", action="store_true", help="Clear response cache"
    )
    parser.add_argument(
        "--stream", action="store_true", help="Enable streaming responses in chat"
    )
    parser.add_argument(
        "--no-stream", action="store_true", help="Disable streaming responses"
    )
    parser.add_argument(
        "--rate-status", action="store_true", help="Show rate limit status"
    )
    parser.add_argument(
        "--reset-rate", action="store_true", help="Reset rate limiter state"
    )
    parser.add_argument(
        "--fallback-status", action="store_true", help="Show fallback manager status"
    )
    parser.add_argument(
        "--clear-blacklist", action="store_true", help="Clear blacklisted models"
    )
    parser.add_argument(
        "--add-fallback",
        metavar="MODEL_ID",
        type=str,
        help="Add model to fallback list",
    )
    parser.add_argument(
        "--remove-fallback",
        metavar="MODEL_ID",
        type=str,
        help="Remove model from fallback list",
    )
    parser.add_argument(
        "--chat", metavar="MODEL_ID", type=str, help="Open chat with a specific model"
    )
    parser.add_argument(
        "--profile-chat",
        metavar="PROFILE_NAME",
        type=str,
        help="Open chat with a profile",
    )
    parser.add_argument(
        "--list-sessions", action="store_true", help="List all chat sessions"
    )
    parser.add_argument(
        "--load-session",
        metavar="SESSION_ID",
        type=str,
        help="Load a previous chat session",
    )
    parser.add_argument(
        "--export-session", metavar="SESSION_ID", type=str, help="Export a chat session"
    )
    parser.add_argument(
        "--ping", action="store_true", help="Start real-time model pinger"
    )
    parser.add_argument(
        "--list-configs", action="store_true", help="List all configurations"
    )
    parser.add_argument(
        "--list-profiles", action="store_true", help="List all profiles"
    )
    parser.add_argument("--list-skills", action="store_true", help="List all skills")
    parser.add_argument(
        "--create-profile", metavar="NAME", type=str, help="Create a new profile"
    )
    parser.add_argument(
        "--use-profile", metavar="NAME", type=str, help="Use specific profile"
    )
    parser.add_argument(
        "--show-config", metavar="NAME", type=str, help="Show configuration"
    )
    parser.add_argument(
        "--registry", action="store_true", help="Create a registry of all models"
    )
    parser.add_argument(
        "--select",
        action="store_true",
        help="Interactive model selection from the registry",
    )
    parser.add_argument(
        "--check", action="store_true", help="Check out all free models"
    )
    parser.add_argument(
        "--list", action="store_true", help="Show working models from the cache"
    )
    parser.add_argument(
        "--test", metavar="MODEL_ID", type=str, help="Check a specific model"
    )
    parser.add_argument(
        "--update", action="store_true", help="Update working model cache"
    )
    parser.add_argument("--api-key", action="store_true", help="Show API key status")
    parser.add_argument(
        "--models", action="store_true", help="Show all available models"
    )
    parser.add_argument(
        "--workers", type=int, default=5, help="Number of parallel threads (default: 5)"
    )
    args = parser.parse_args()
    # if not arg
    if not any(vars(args).values()):
        parser.print_help()
        return 0
    # Write banner
    print_banner()
    # Check API key
    if not API_KEY:
        print_error("API_KEY не найден в .env файле")
        print_info(
            "Create a .env file with the following content: OPENROUTER_KEY=sk-or-v1-xxx"
        )
        return 1
    # Create an instance of the validator.
    checker = ApiKeyChecker(API_KEY)
    # Executing the command.
    try:
        if args.check or args.update:
            return cmd_check(checker, args.workers)
        elif args.list:
            return cmd_list()
        elif args.test:
            return cmd_test(checker, args.test)
        elif args.api_key:
            return cmd_api_key(checker)
        elif args.models:
            return cmd_models(checker)
        elif args.registry:
            return cmd_create_registry(checker)
        elif args.select:
            return cmd_select(checker)
        elif args.list_configs:
            return cmd_list_configs()
        elif args.list_profiles:
            return cmd_list_profiles()
        elif args.rate_status:
            return cmd_rate_status(checker)
        elif args.reset_rate:
            return cmd_reset_rate(checker)
        elif args.list_skills:
            return cmd_list_skills()
        elif args.create_profile:
            return cmd_create_profile(args)
        elif args.show_config:
            return cmd_show_config(args)
        elif args.use_profile:
            return cmd_chat(checker, args.use_profile)
        elif args.chat:
            return cmd_chat(checker, args.use_profile)
        elif args.ping:
            return cmd_ping()
        elif args.fallback_status:
            return cmd_fallback_status(checker)
        elif args.clear_blacklist:
            return cmd_clear_blacklist(checker)
        elif args.add_fallback:
            return cmd_add_fallback(checker, args.add_fallback)
        elif args.remove_fallback:
            return cmd_remove_fallback(checker, args.remove_fallback)
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        print_warning("Operation interrupted by the user")
        return 130
    except Exception as e:
        print_error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


def _print_stats(session: "ChatSession") -> None:
    """Print session statistics"""
    stats = session.get_stats()
    print(f"\n{Colors.CYAN}{Colors.BOLD}Session Statistics{Colors.END}")
    print(f"{Colors.DIM}{'=' * 50}{Colors.END}")
    print(f"Model:           {Colors.CYAN}{stats['model']}{Colors.END}")
    print(f"Profile:         {Colors.GREEN}{stats['profile']}{Colors.END}")
    print(f"Messages:        {stats['messages']}")
    print(f"Input Tokens:    {stats['input_tokens']}")
    print(f"Output Tokens:   {stats['output_tokens']}")
    print(f"Total Tokens:    {stats['total_tokens']}")
    print(f"Duration:        {stats['duration_seconds']:.1f}s")
    print(f"Est. Cost:       ${stats['estimated_cost']:.6f}")
    print(f"Created:         {stats['created_at']}")
    print(f"{Colors.DIM}{'=' * 50}{Colors.END}\n")


def _print_status_bar(session: "ChatSession", session_id: str) -> None:
    """Print session status bar"""
    model_display = (
        session.model_id.split("/")[-1] if "/" in session.model_id else session.model_id
    )
    profile_display = session.profile or "default"
    status = f"[{Colors.CYAN}{model_display}{Colors.END}] [{Colors.GREEN}{profile_display}{Colors.END}] [{Colors.YELLOW}#{session_id[-8:]}{Colors.END}] Msgs: {session.message_count} Tokens: {session.input_tokens + session.output_tokens}"
    print(f"{Colors.DIM}─ {status}{Colors.END}")


def _get_multiline_input(prompt: str = "You: ") -> str:
    """Get multiline input from user (Ctrl+D or Ctrl+Z to finish)"""
    print(f"{prompt}", end="", flush=True)
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()
