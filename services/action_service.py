import logging
import json
import re
from datetime import date
from database import execute_read_query

logger = logging.getLogger(__name__)

ACTION_START = "---ACTION---"
ACTION_END = "---END_ACTION---"


class ActionService:
    """Detects, parses, and resolves action intents from LLM responses."""

    def search_customer(self, name: str) -> list[dict]:
        """Search customers by name (fuzzy)."""
        query = (
            "SELECT id, first_name, last_name, company_name, phone, email "
            "FROM customers_customer "
            "WHERE (first_name || ' ' || last_name LIKE :name "
            "OR company_name LIKE :name) "
            "AND is_active = 1 "
            "ORDER BY first_name LIMIT 5"
        )
        return execute_read_query(query, {"name": f"%{name}%"})

    def search_chemical(self, name: str) -> list[dict]:
        """Search chemicals by name (fuzzy)."""
        query = (
            "SELECT id, chemical_name, chemical_code, selling_price, unit, quantity, gst_percentage "
            "FROM inventory_chemical "
            "WHERE chemical_name LIKE :name OR chemical_code LIKE :name "
            "ORDER BY chemical_name LIMIT 5"
        )
        return execute_read_query(query, {"name": f"%{name}%"})

    def parse_action_from_response(self, response: str) -> tuple[str, dict | None]:
        """Extract action JSON from LLM response. Returns (clean_text, action_data)."""
        if ACTION_START not in response:
            return response, None

        try:
            start_idx = response.index(ACTION_START)
            end_idx = response.index(ACTION_END) + len(ACTION_END)

            # Extract and clean the text
            clean_text = (response[:start_idx] + response[end_idx:]).strip()

            # Extract JSON
            json_str = response[start_idx + len(ACTION_START):response.index(ACTION_END)].strip()
            action_data = json.loads(json_str)

            return clean_text, action_data
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse action from response: {e}")
            # Strip the markers even if parsing fails
            cleaned = re.sub(r'---ACTION---.*?---END_ACTION---', '', response, flags=re.DOTALL).strip()
            return cleaned, None

    def resolve_action(self, action_data: dict) -> dict:
        """Resolve names to IDs and add details for frontend execution."""
        action_type = action_data.get("type", "")

        if action_type == "create_order":
            return self._resolve_create_order(action_data)
        elif action_type == "create_customer":
            return self._resolve_create_customer(action_data)
        else:
            return {
                "type": action_type,
                "resolved": False,
                "error": f"Unknown action type: {action_type}",
            }

    def _resolve_create_order(self, action_data: dict) -> dict:
        """Resolve a create_order action."""
        result = {
            "type": "create_order",
            "resolved": True,
            "dashboard_link": "/orders",
            "params": {
                "order_date": action_data.get("order_date", date.today().isoformat()),
                "status": "pending",
                "payment_status": "unpaid",
                "notes": action_data.get("notes", ""),
                "discount_amount": str(action_data.get("discount_amount", "0.00")),
                "items": [],
            },
            "display": {
                "customer": None,
                "items": [],
                "summary": "",
            },
            "errors": [],
        }

        # Resolve customer
        customer_name = action_data.get("customer_name", "")
        if customer_name:
            customers = self.search_customer(customer_name)
            if len(customers) == 1:
                c = customers[0]
                result["params"]["customer"] = c["id"]
                full_name = f"{c['first_name']} {c['last_name']}"
                company = f" ({c['company_name']})" if c.get("company_name") else ""
                result["display"]["customer"] = f"{full_name}{company}"
            elif len(customers) > 1:
                names = [f"{c['first_name']} {c['last_name']}" for c in customers]
                result["resolved"] = False
                result["errors"].append(f"Multiple customers found for '{customer_name}': {', '.join(names)}. Please specify which one.")
            else:
                result["resolved"] = False
                result["errors"].append(f"Customer '{customer_name}' not found.")
        else:
            result["resolved"] = False
            result["errors"].append("No customer specified.")

        # Resolve items
        items = action_data.get("items", [])
        for item in items:
            chem_name = item.get("chemical_name", "")
            quantity = item.get("quantity", 0)

            if not chem_name:
                result["errors"].append("An item is missing a chemical name.")
                continue

            chemicals = self.search_chemical(chem_name)
            if len(chemicals) == 1:
                chem = chemicals[0]
                unit_price = item.get("unit_price", chem.get("selling_price", 0))
                resolved_item = {
                    "chemical": chem["id"],
                    "quantity": str(quantity),
                    "unit_price": str(unit_price),
                    "specifications": item.get("specifications", ""),
                }
                result["params"]["items"].append(resolved_item)
                result["display"]["items"].append({
                    "name": chem["chemical_name"],
                    "quantity": quantity,
                    "unit": chem.get("unit", ""),
                    "unit_price": float(unit_price),
                    "stock": chem.get("quantity", 0),
                })
            elif len(chemicals) > 1:
                names = [c["chemical_name"] for c in chemicals]
                result["resolved"] = False
                result["errors"].append(f"Multiple chemicals found for '{chem_name}': {', '.join(names)}. Please specify which one.")
            else:
                result["resolved"] = False
                result["errors"].append(f"Chemical '{chem_name}' not found in inventory.")

        if not result["params"]["items"] and not result["errors"]:
            result["resolved"] = False
            result["errors"].append("No items specified for the order.")

        # Build display summary
        if result["display"]["items"]:
            total = sum(i["quantity"] * i["unit_price"] for i in result["display"]["items"])
            result["display"]["summary"] = f"Order total: INR {total:,.2f}"

        return result

    def _resolve_create_customer(self, action_data: dict) -> dict:
        """Resolve a create_customer action."""
        result = {
            "type": "create_customer",
            "resolved": True,
            "dashboard_link": "/customers",
            "params": {
                "first_name": action_data.get("first_name", ""),
                "last_name": action_data.get("last_name", ""),
                "company_name": action_data.get("company_name", ""),
                "email": action_data.get("email", ""),
                "phone": action_data.get("phone", ""),
                "address": action_data.get("address", ""),
                "city": action_data.get("city", ""),
                "state": action_data.get("state", ""),
            },
            "display": {
                "name": f"{action_data.get('first_name', '')} {action_data.get('last_name', '')}".strip(),
                "summary": "",
            },
            "errors": [],
        }

        if not result["params"]["first_name"]:
            result["resolved"] = False
            result["errors"].append("First name is required.")

        return result


action_service = ActionService()
