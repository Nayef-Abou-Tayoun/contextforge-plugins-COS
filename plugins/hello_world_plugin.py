"""
Simple Hello World Plugin for Testing COS Plugin Loading

This plugin adds a simple greeting tool to demonstrate dynamic plugin loading from COS.
"""
from typing import Any, Dict
import logging
from cpex.framework import PluginConfig

logger = logging.getLogger(__name__)


class HelloWorldPlugin:
    """A simple plugin that adds a greeting tool."""
    
    def __init__(self, config: PluginConfig):
        """Initialize the Hello World plugin.
        
        Args:
            config: Plugin configuration from the framework
        """
        self.config = config
        self.name = "hello_world"
        self.version = "1.0.0"
        self.hooks = []  # This plugin doesn't implement any hooks
        logger.info(f"HelloWorldPlugin v{self.version} initialized")
    
    async def initialize(self):
        """Initialize the plugin (called by framework after instantiation)."""
        logger.info(f"HelloWorldPlugin v{self.version} initialization complete")
    
    def get_tools(self) -> list[Dict[str, Any]]:
        """Return the list of tools provided by this plugin."""
        return [
            {
                "name": "say_hello",
                "description": "Returns a friendly greeting message",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the person to greet"
                        }
                    },
                    "required": ["name"]
                }
            }
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool provided by this plugin."""
        if tool_name == "say_hello":
            name = arguments.get("name", "World")
            message = f"Hello, {name}! This greeting comes from a plugin loaded dynamically from IBM Cloud Object Storage! 🎉"
            logger.info(f"HelloWorldPlugin: Generated greeting for {name}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": message
                    }
                ],
                "isError": False
            }
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Unknown tool: {tool_name}"
                }
            ],
            "isError": True
        }


# Plugin factory function (required)
def create_plugin():
    """Factory function to create plugin instance."""
    return HelloWorldPlugin()

# Made with Bob
