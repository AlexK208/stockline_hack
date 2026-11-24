"""
The tools the model can call, grouped by domain. Each one wraps ERP API endpoints.

    registry.py  @tool decorator, Tool, ToolContext (start here to add a tool)
    erp.py       the HTTP client for the ERP API
    catalog.py   search, get_client, get_product_stock, find_alternatives, get_price
    context.py   search_context, get_context, save_context
    history.py   get_client_history, log_client_event, get_supplier_history, log_supplier_event
    orders.py    create_draft_order, add_order_line, update_order_line, remove_order_line, update_order, cancel_order,
                 confirm_order, get_order
    desk.py      identify_caller, check_products, order_history (composite: one call per turn)
    truck.py     truck_call_brief, add_to_truck, take_off_truck (the outgoing call before the truck leaves)
    festive.py   festive_history, festive_availability, festive_reserve, festive_cancel (le carnet des fêtes)
    cotation.py  cotation_semaine (le cadran annoncé : la variation de la semaine sur ses carcasses)

A new file needs one more line: import it below so its @tool functions get registered.
"""

from . import desk, catalog, context, history, orders, suggest, truck, festive, cotation  # noqa: F401  (importing registers the tools)
from .erp import ErpClient
from .registry import TOOLS, Tool, ToolContext, tool


def all_tools() -> list[Tool]:
    return list(TOOLS.values())


__all__ = ["TOOLS", "ErpClient", "Tool", "ToolContext", "all_tools", "tool"]
