"""HTTP / WebSocket routes. Thin: parse the request, call the agent or a service, stream the result."""

from . import chat, command, health, outbound, speech, voice
from . import allocation  # after outbound: it imports services.truck_calls, which must load the tools first

routers = [health.router, chat.router, command.router, speech.router, voice.router, outbound.router, allocation.router]
