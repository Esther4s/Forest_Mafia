# Overview

"Лес и Волки" is a Telegram bot that implements a forest-themed version of the classic Mafia party game. Players are assigned roles as various forest animals divided into two teams: predators (wolves and fox) and herbivores (hares, mole, and beaver). The game alternates between night and day phases, where predators hunt their prey while herbivores try to survive and identify the threats during voting phases.

# User Preferences

Preferred communication style: Simple, everyday language.

# Recent Changes

## September 2025
- **Simplified authorization system**: Bot now automatically authorizes chats when players use game commands
- **Auto-setup functionality**: No need to run `/setup_channel` before starting games - bot works immediately in any chat
- **Enhanced user experience**: Players can use `/join` and other commands right away without admin setup
- **Maintained security**: Admin commands `/setup_channel` and `/remove_channel` still available for advanced management
- **Improved logging**: All authorization and permission events are logged for monitoring
- **Smart channel management**: Authorized channels are tracked automatically and persist during bot session
- **Fixed game logic**: Corrected premature game ending for 6-player games - now only ends in draw at final 1v1 confrontation
- **Balanced gameplay**: Game continues properly with 4+ players instead of ending in automatic draw
- **Topics support**: Added full support for Telegram Topics - bot can now work in specific topics within a chat
- **Thread-specific authorization**: `/setup_channel` command now registers bot for specific topic only, not entire chat
- **Enhanced privacy**: Bot ignores messages from other topics in the same chat, providing better isolation

# System Architecture

## Core Game Engine
The application follows a modular architecture with clear separation of concerns:

- **Game Logic Core** (`game_logic.py`): Implements the main game state management, player roles, teams, and phase transitions using Python dataclasses and enums
- **Night Actions System** (`night_actions.py`): Handles special abilities during night phases, including wolf attacks, fox stealing, beaver protection, and mole investigations
- **Night Interface** (`night_interface.py`): Provides interactive Telegram inline keyboards for players to select targets and perform actions during night phases
- **Bot Controller** (`bot.py`): Manages Telegram bot interactions, command handling, and coordinates between game components

## Game State Management
The system uses in-memory storage with dictionary-based game sessions:
- Games are stored per chat ID to support multiple concurrent games
- Player states track roles, teams, alive status, and special conditions (fox theft count, beaver protection)
- Global settings are managed through JSON configuration files for easy runtime adjustments

## Telegram Integration
The bot leverages python-telegram-bot library for:
- Command handlers for game control (`/start`, `/join`, `/leave`, `/start_game`, etc.)
- Callback query handlers for interactive buttons and menus
- Inline keyboards for night action selections and game navigation
- Message pinning for persistent game status displays

## Configuration System
Settings are managed through multiple layers:
- Environment variables for sensitive data (bot tokens)
- JSON configuration files for game parameters and role distributions
- Global settings class for runtime configuration management
- Test mode support for reduced player requirements during development

## Role Distribution Algorithm
The game implements a percentage-based role assignment system:
- Wolves: 25% of players
- Fox: 15% of players  
- Hares: 35% of players
- Mole: 15% of players
- Beaver: 10% of players

This ensures balanced gameplay regardless of player count while maintaining the competitive dynamics between teams.

# External Dependencies

## Telegram Bot API
- **python-telegram-bot[job-queue]**: Primary framework for Telegram bot functionality, including message handling, inline keyboards, and callback management
- **BotFather Integration**: Bot token management and configuration through Telegram's official bot creation service

## Configuration Management  
- **python-dotenv**: Environment variable loading for secure token storage and configuration management

## Runtime Environment
- **Python 3.7+**: Core runtime requirement
- **asyncio**: Asynchronous programming support for handling concurrent game sessions and Telegram API calls
- **JSON**: Built-in configuration file management for game settings persistence

## Development and Testing
- **logging**: Built-in Python logging for debugging and monitoring bot operations
- **unittest/testing modules**: Custom test files for validating game logic, night actions, and feature implementations

The bot is designed to run as a standalone application without external databases, using in-memory storage for game sessions and JSON files for persistent configuration.