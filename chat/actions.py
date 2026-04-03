import logging
import json
import re
from datetime import date
from database import execute_read_query

logger = logging.getLogger(__name__)

ACTION_START = "---ACTION---"
ACTION_END = "---END_ACTION---"
PLAN_START = "---ACTION_PLAN---"
PLAN_END = "---END_ACTION_PLAN---"

# Risk thresholds
HIGH_RISK_INVENTORY_QTY = 1000


class ActionService:
    """Detects, parses, and resolves action intents from LLM responses."""

    # ── Database lookups ──────────────────────────────────────────────

    def search_customer(self, name: str) -> list[dict]:
        """Search customers by name (fuzzy)."""
        query = (
            "SELECT id, first_name, last_name, company_name, phone, email "
            "FROM customers "
            "WHERE (first_name || ' ' || last_name LIKE :name "
            "OR company_name LIKE :name) "
            "AND is_active = true "
            "ORDER BY first_name LIMIT 5"
        )
        return execute_read_query(query, {"name": f"%{name}%"})

    def search_chemical(self, name: str) -> list[dict]:
        """Search chemicals by name (fuzzy)."""
        query = (
            "SELECT id, chemical_name, chemical_code, selling_price, unit, "
            "quantity, gst_percentage, purchase_price, category_id "
            "FROM chemicals "
            "WHERE chemical_name LIKE :name OR chemical_code LIKE :name "
            "ORDER BY chemical_name LIMIT 5"
        )
        return execute_read_query(query, {"name": f"%{name}%"})

    def search_category(self, name: str) -> list[dict]:
        """Search categories by name."""
        query = (
            "SELECT id, name FROM categories "
            "WHERE name LIKE :name ORDER BY name LIMIT 5"
        )
        return execute_read_query(query, {"name": f"%{name}%"})

    def get_default_category(self) -> dict | None:
        """Get the first category as default."""
        result = execute_read_query(
            "SELECT id, name FROM categories ORDER BY id LIMIT 1"
        )
        return result[0] if result else None

    # ── Response parsing ──────────────────────────────────────────────

    def parse_action_from_response(self, response: str) -> tuple[str, dict | None, dict | None]:
        """Extract action or action plan from LLM response.
        Returns (clean_text, single_action_data, plan_data).
        """
        # Check for action plan first
        if PLAN_START in response:
            return self._parse_action_plan(response)

        # Check for single action
        if ACTION_START in response:
            clean_text, action_data = self._parse_single_action(response)
            return clean_text, action_data, None

        return response, None, None

    def _parse_single_action(self, response: str) -> tuple[str, dict | None]:
        """Extract single action JSON from response."""
        try:
            start_idx = response.index(ACTION_START)
            end_idx = response.index(ACTION_END) + len(ACTION_END)
            clean_text = (response[:start_idx] + response[end_idx:]).strip()
            json_str = response[start_idx + len(ACTION_START):response.index(ACTION_END)].strip()
            action_data = json.loads(json_str)
            return clean_text, action_data
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse action from response: {e}")
            cleaned = re.sub(
                r'---ACTION---.*?---END_ACTION---', '', response, flags=re.DOTALL
            ).strip()
            return cleaned, None

    def _parse_action_plan(self, response: str) -> tuple[str, None, dict | None]:
        """Extract multi-step action plan from response."""
        try:
            start_idx = response.index(PLAN_START)
            end_idx = response.index(PLAN_END) + len(PLAN_END)
            clean_text = (response[:start_idx] + response[end_idx:]).strip()
            json_str = response[start_idx + len(PLAN_START):response.index(PLAN_END)].strip()
            plan_data = json.loads(json_str)
            return clean_text, None, plan_data
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse action plan from response: {e}")
            cleaned = re.sub(
                r'---ACTION_PLAN---.*?---END_ACTION_PLAN---', '', response, flags=re.DOTALL
            ).strip()
            return cleaned, None, None

    # ── Single action resolution (backward compatible) ────────────────

    def resolve_action(self, action_data: dict) -> dict:
        """Resolve a single action, or upgrade to a plan if dependencies are missing."""
        action_type = action_data.get("type", "")

        if action_type == "create_order":
            resolved = self._resolve_create_order(action_data)
            # Check if we need to upgrade to a multi-step plan
            plan = self._maybe_upgrade_to_plan(action_data, resolved)
            if plan:
                return {"_is_plan": True, "plan": plan}
            return resolved
        elif action_type == "create_customer":
            return self._resolve_create_customer(action_data)
        elif action_type == "create_chemical":
            return self._resolve_create_chemical(action_data)
        elif action_type == "update_inventory":
            return self._resolve_update_inventory(action_data)
        else:
            return {
                "type": action_type,
                "resolved": False,
                "error": f"Unknown action type: {action_type}",
            }

    def _maybe_upgrade_to_plan(self, action_data: dict, resolved: dict) -> dict | None:
        """If a create_order has missing customer or chemicals, build a plan."""
        if resolved["resolved"]:
            return None  # Everything resolved fine, no plan needed

        errors = resolved.get("errors", [])
        steps = []
        step_counter = 0

        # Check for missing customer
        customer_name = action_data.get("customer_name", "")
        customer_missing = any("not found" in e.lower() and "customer" in e.lower() for e in errors)

        if customer_missing and customer_name:
            step_counter += 1
            parts = customer_name.strip().split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""
            steps.append({
                "step_id": f"step{step_counter}",
                "type": "create_customer",
                "params": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "company_name": "",
                    "phone": "",
                    "city": "",
                    "state": "",
                },
                "display": {"name": customer_name},
                "depends_on": [],
                "auto_execute": True,
                "risk_level": "low",
                "errors": [],
                "resolved": True,
            })

        # Check for missing chemicals
        items = action_data.get("items", [])
        for item in items:
            chem_name = item.get("chemical_name", "")
            chem_missing = any(
                "not found" in e.lower() and chem_name.lower() in e.lower()
                for e in errors
            )
            if chem_missing and chem_name:
                step_counter += 1
                code = re.sub(r'[^A-Z0-9]', '', chem_name.upper())[:10] + "-001"
                unit_price = item.get("unit_price", 0)
                steps.append({
                    "step_id": f"step{step_counter}",
                    "type": "create_chemical",
                    "params": {
                        "chemical_name": chem_name,
                        "chemical_code": code,
                        "unit": "KG",
                        "quantity": 0,
                        "min_quantity": 100,
                        "purchase_price": str(round(float(unit_price) * 0.7, 2)) if unit_price else "0",
                        "selling_price": str(unit_price) if unit_price else "0",
                        "gst_percentage": "18.00",
                    },
                    "display": {
                        "name": chem_name,
                        "code": code,
                        "selling_price": float(unit_price) if unit_price else 0,
                    },
                    "depends_on": [],
                    "auto_execute": True,
                    "risk_level": "low",
                    "errors": [],
                    "resolved": True,
                })

        if not steps:
            return None  # Nothing to auto-create, keep as single failed action

        # Add the order step at the end
        step_counter += 1
        order_step = {
            "step_id": f"step{step_counter}",
            "type": "create_order",
            "params": {
                "order_date": action_data.get("order_date", date.today().isoformat()),
                "status": "pending",
                "payment_status": "unpaid",
                "notes": action_data.get("notes", ""),
                "discount_amount": str(action_data.get("discount_amount", "0.00")),
                "customer_name": customer_name,
                "items": items,
            },
            "display": {
                "customer": customer_name,
                "items": [
                    {
                        "name": i.get("chemical_name", ""),
                        "quantity": i.get("quantity", 0),
                        "unit_price": float(i.get("unit_price", 0)),
                    }
                    for i in items
                ],
            },
            "depends_on": [s["step_id"] for s in steps],
            "auto_execute": False,
            "risk_level": "high",
            "errors": [],
            "resolved": True,
        }
        steps.append(order_step)

        return {
            "steps": steps,
            "summary": f"Create prerequisites and place order for {customer_name}",
            "has_high_risk": True,
        }

    # ── Action plan resolution ────────────────────────────────────────

    def resolve_action_plan(self, plan_data: dict) -> dict:
        """Resolve a multi-step action plan from the LLM."""
        steps_data = plan_data.get("steps", [])
        resolved_steps = []

        for step in steps_data:
            step_type = step.get("type", "")
            step_id = step.get("step_id", f"step{len(resolved_steps) + 1}")
            depends_on = step.get("depends_on", [])

            if step_type == "create_customer":
                resolved = self._resolve_create_customer(step)
                risk = "low"
                auto = True
            elif step_type == "create_chemical":
                resolved = self._resolve_create_chemical(step)
                risk = "low"
                auto = True
            elif step_type == "create_order":
                resolved = self._resolve_create_order_for_plan(step)
                risk = "high"
                auto = False
            elif step_type == "update_inventory":
                resolved = self._resolve_update_inventory(step)
                qty = float(step.get("quantity", 0))
                risk = "high" if qty > HIGH_RISK_INVENTORY_QTY else "low"
                auto = risk == "low"
            else:
                resolved = {"resolved": False, "errors": [f"Unknown step type: {step_type}"]}
                risk = "high"
                auto = False

            resolved_steps.append({
                "step_id": step_id,
                "type": step_type,
                "params": resolved.get("params", {}),
                "display": resolved.get("display", {}),
                "depends_on": depends_on,
                "auto_execute": auto,
                "risk_level": risk,
                "errors": resolved.get("errors", []),
                "resolved": resolved.get("resolved", False),
            })

        has_high = any(s["risk_level"] == "high" for s in resolved_steps)

        return {
            "steps": resolved_steps,
            "summary": plan_data.get("summary", "Multi-step action plan"),
            "has_high_risk": has_high,
        }

    # ── Individual resolvers ──────────────────────────────────────────

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
                result["errors"].append(
                    f"Multiple customers found for '{customer_name}': {', '.join(names)}. Please specify which one."
                )
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
                result["errors"].append(
                    f"Multiple chemicals found for '{chem_name}': {', '.join(names)}. Please specify which one."
                )
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

    def _resolve_create_order_for_plan(self, step_data: dict) -> dict:
        """Resolve order step within a plan (may have unresolved dependencies)."""
        result = {
            "resolved": True,
            "params": {
                "order_date": step_data.get("order_date", date.today().isoformat()),
                "status": "pending",
                "payment_status": "unpaid",
                "notes": step_data.get("notes", ""),
                "discount_amount": str(step_data.get("discount_amount", "0.00")),
                "customer_name": step_data.get("customer_name", ""),
                "items": step_data.get("items", []),
            },
            "display": {
                "customer": step_data.get("customer_name", ""),
                "items": [
                    {
                        "name": i.get("chemical_name", ""),
                        "quantity": i.get("quantity", 0),
                        "unit_price": float(i.get("unit_price", 0)),
                    }
                    for i in step_data.get("items", [])
                ],
                "summary": "",
            },
            "errors": [],
        }

        # Calculate summary
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
                "address_line1": action_data.get("address", ""),
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

    def _resolve_create_chemical(self, action_data: dict) -> dict:
        """Resolve a create_chemical action."""
        chemical_name = action_data.get("chemical_name", "")
        chemical_code = action_data.get("chemical_code", "")
        category_name = action_data.get("category_name", "")

        result = {
            "type": "create_chemical",
            "resolved": True,
            "dashboard_link": "/inventory",
            "params": {
                "chemical_name": chemical_name,
                "chemical_code": chemical_code,
                "unit": action_data.get("unit", "KG"),
                "quantity": str(action_data.get("quantity", 0)),
                "min_quantity": str(action_data.get("min_quantity", 100)),
                "purchase_price": str(action_data.get("purchase_price", 0)),
                "selling_price": str(action_data.get("selling_price", 0)),
                "gst_percentage": str(action_data.get("gst_percentage", 18)),
            },
            "display": {
                "name": chemical_name,
                "code": chemical_code,
                "unit": action_data.get("unit", "KG"),
                "selling_price": float(action_data.get("selling_price", 0)),
                "gst": float(action_data.get("gst_percentage", 18)),
            },
            "errors": [],
        }

        # Validate required fields
        if not chemical_name:
            result["resolved"] = False
            result["errors"].append("Chemical name is required.")
        if not chemical_code:
            # Auto-generate code
            code = re.sub(r'[^A-Z0-9]', '', chemical_name.upper())[:10] + "-001"
            result["params"]["chemical_code"] = code
            result["display"]["code"] = code

        # Check if chemical already exists
        if chemical_name:
            existing = self.search_chemical(chemical_name)
            exact = [c for c in existing if c["chemical_name"].lower() == chemical_name.lower()]
            if exact:
                result["resolved"] = False
                result["errors"].append(
                    f"Chemical '{chemical_name}' already exists (code: {exact[0]['chemical_code']})."
                )
                return result

        # Resolve category
        if category_name:
            categories = self.search_category(category_name)
            if categories:
                result["params"]["category"] = categories[0]["id"]
                result["display"]["category"] = categories[0]["name"]
            else:
                # Category doesn't exist - we'll let the frontend handle or skip
                result["display"]["category"] = category_name
        else:
            default_cat = self.get_default_category()
            if default_cat:
                result["params"]["category"] = default_cat["id"]
                result["display"]["category"] = default_cat["name"]

        return result

    def _resolve_update_inventory(self, action_data: dict) -> dict:
        """Resolve an update_inventory (stock entry) action."""
        chemical_name = action_data.get("chemical_name", "")
        quantity = action_data.get("quantity", 0)
        entry_type = action_data.get("entry_type", "purchase")
        rate = action_data.get("rate", 0)

        result = {
            "type": "update_inventory",
            "resolved": True,
            "dashboard_link": "/inventory",
            "params": {
                "entry_type": entry_type,
                "quantity": str(quantity),
                "rate": str(rate),
                "reference_note": action_data.get("reference_note", ""),
            },
            "display": {
                "chemical": None,
                "quantity": quantity,
                "entry_type": entry_type,
                "rate": float(rate),
            },
            "errors": [],
        }

        if not chemical_name:
            result["resolved"] = False
            result["errors"].append("Chemical name is required.")
            return result

        chemicals = self.search_chemical(chemical_name)
        if len(chemicals) == 1:
            chem = chemicals[0]
            result["params"]["chemical"] = chem["id"]
            result["display"]["chemical"] = chem["chemical_name"]
            result["display"]["current_stock"] = float(chem.get("quantity", 0))
            result["display"]["unit"] = chem.get("unit", "KG")
            if not rate:
                result["params"]["rate"] = str(chem.get("purchase_price", 0))
                result["display"]["rate"] = float(chem.get("purchase_price", 0))
        elif len(chemicals) > 1:
            names = [c["chemical_name"] for c in chemicals]
            result["resolved"] = False
            result["errors"].append(
                f"Multiple chemicals found for '{chemical_name}': {', '.join(names)}. Please specify."
            )
        else:
            result["resolved"] = False
            result["errors"].append(f"Chemical '{chemical_name}' not found in inventory.")

        return result


action_service = ActionService()
