# Overview

"Лесная Возня" is a Telegram bot that implements a forest-themed version of the classic Mafia party game. Players are assigned roles as various forest animals divided into two teams: predators (wolves and fox) and herbivores (hares, mole, and beaver). The game alternates between night and day phases, where predators hunt their prey while herbivores try to survive and identify the threats during voting phases.

# User Preferences

Preferred communication style: Simple, everyday language.

# Recent Changes

## September 2025
- **Added authorization system**: Bot now only responds in channels specifically set up via `/setup_channel`
- **Enhanced security**: Bot silently ignores commands in non-authorized channels
- **Added `/remove_channel` command**: Administrators can remove channels from authorized list  
- **Improved logging**: All authorization and permission events are logged for monitoring
- **Channel management**: Authorized channels are tracked in memory and persist during bot session

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