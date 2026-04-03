import logging
import re
from database import execute_read_query
from core.market_pricing import market_pricing_service

logger = logging.getLogger(__name__)

# Common chemical keywords to detect in messages
CHEMICAL_KEYWORDS = [
    "acid", "sulfuric", "hydrochloric", "nitric", "phosphoric", "acetic",
    "sodium", "hydroxide", "caustic", "soda", "chloride", "carbonate",
    "potassium", "calcium", "magnesium", "zinc", "copper", "iron",
    "ammonia", "peroxide", "permanganate", "sulfate", "hcl", "h2so4",
    "naoh", "chemical", "price", "rate", "market", "cost",
]


class ChatContextService:
    """Reads ERP database to build LLM context for chat."""

    def get_business_summary(self) -> str:
        """Get a high-level business summary for LLM context."""
        sections = []

        # Customer stats
        customers = execute_read_query(
            "SELECT COUNT(*) as total, SUM(CASE WHEN is_active = true THEN 1 ELSE 0 END) as active "
            "FROM customers"
        )
        if customers:
            c = customers[0]
            sections.append(f"Customers: {c['total']} total, {c['active']} active")

        # Order stats
        orders = execute_read_query(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending, "
            "SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered "
            "FROM orders"
        )
        if orders:
            o = orders[0]
            sections.append(f"Orders: {o['total']} total, {o['pending']} pending, {o['delivered']} delivered")

        # Revenue
        revenue = execute_read_query(
            "SELECT COALESCE(SUM(total_amount), 0) as total_revenue "
            "FROM orders WHERE payment_status = 'paid'"
        )
        if revenue:
            sections.append(f"Total Revenue (paid): INR {revenue[0]['total_revenue']:,.2f}")

        # Inventory
        inventory = execute_read_query(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN quantity <= min_quantity THEN 1 ELSE 0 END) as low_stock "
            "FROM chemicals"
        )
        if inventory:
            inv = inventory[0]
            sections.append(f"Inventory: {inv['total']} chemicals, {inv['low_stock']} low stock")

        if not sections:
            return "Business data is currently unavailable."

        return "Current Business Overview:\n" + "\n".join(f"- {s}" for s in sections)

    def get_context_for_type(self, context_type: str) -> str:
        """Get detailed context based on the requested type."""
        handlers = {
            "general": self._general_context,
            "sales": self._sales_context,
            "inventory": self._inventory_context,
            "customers": self._customers_context,
            "orders": self._orders_context,
        }
        handler = handlers.get(context_type, self._general_context)
        try:
            return handler()
        except Exception as e:
            logger.error(f"Error getting context for {context_type}: {e}")
            return "Detailed business data is currently unavailable."

    async def get_market_pricing_context(self, message: str) -> str:
        """Get market pricing context based on user message."""
        try:
            chemicals_to_price = self._extract_chemicals_from_message(message)

            if not chemicals_to_price:
                return ""

            prices = await market_pricing_service.get_bulk_prices(chemicals_to_price)
            available = [p for p in prices if p.get("available")]

            if not available:
                return ""

            lines = ["Current Indian Market Prices (from IndiaMART):"]
            for p in available:
                if p["price_min"] == p["price_max"]:
                    price_str = f"INR {p['price_min']:,.2f}"
                else:
                    price_str = f"INR {p['price_min']:,.2f} - {p['price_max']:,.2f}"
                lines.append(f"- {p['chemical']}: {price_str} per {p['unit']} (source: {p['source']})")

            lines.append("Note: Prices are indicative and may vary by quantity, grade, and supplier.")
            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"Failed to get market pricing context: {e}")
            return ""

    def _extract_chemicals_from_message(self, message: str) -> list[str]:
        """Extract chemical names from the user's message to look up prices."""
        message_lower = message.lower()
        chemicals = []

        # Check for known chemicals in inventory
        try:
            db_chemicals = execute_read_query(
                "SELECT chemical_name FROM chemicals ORDER BY chemical_name"
            )
            for chem in db_chemicals:
                name = chem["chemical_name"]
                if name.lower() in message_lower:
                    chemicals.append(name)
        except Exception:
            pass

        # Check for chemical keywords suggesting pricing interest
        has_price_intent = any(
            w in message_lower for w in ["price", "rate", "cost", "market", "pricing", "worth", "value"]
        )

        if has_price_intent and not chemicals:
            # Try to extract chemical names using patterns
            # Look for capitalized words that could be chemical names
            words = message.split()
            for i, word in enumerate(words):
                clean = re.sub(r'[^a-zA-Z0-9]', '', word).lower()
                if clean in [
                    "hcl", "h2so4", "naoh", "nacl", "hno3", "h3po4", "nh3",
                    "cacl2", "na2co3", "koh", "h2o2",
                ]:
                    chemicals.append(clean)
                elif any(kw in clean for kw in [
                    "acid", "sulfat", "chlorid", "hydroxid", "carbonat",
                    "ammonia", "peroxid", "permangan",
                ]):
                    chemicals.append(word.strip('.,!?'))

        return chemicals[:5]  # Limit to 5

    def _general_context(self) -> str:
        return self.get_business_summary()

    def _sales_context(self) -> str:
        sections = [self.get_business_summary()]

        recent = execute_read_query(
            "SELECT o.order_number, o.total_amount, o.status, o.payment_status, "
            "c.first_name || ' ' || c.last_name as customer_name "
            "FROM orders o "
            "JOIN customers c ON o.customer_id = c.id "
            "ORDER BY o.created_at DESC LIMIT 10"
        )
        if recent:
            sections.append("\nRecent Orders:")
            for r in recent:
                sections.append(
                    f"  - {r['order_number']}: INR {r['total_amount']:,.2f} "
                    f"({r['status']}, {r['payment_status']}) - {r['customer_name']}"
                )

        top = execute_read_query(
            "SELECT c.first_name || ' ' || c.last_name as name, "
            "c.company_name, SUM(o.total_amount) as total "
            "FROM orders o "
            "JOIN customers c ON o.customer_id = c.id "
            "WHERE o.payment_status = 'paid' "
            "GROUP BY c.id, c.first_name, c.last_name, c.company_name "
            "ORDER BY total DESC LIMIT 5"
        )
        if top:
            sections.append("\nTop Customers by Revenue:")
            for t in top:
                company = f" ({t['company_name']})" if t.get('company_name') else ""
                sections.append(f"  - {t['name']}{company}: INR {t['total']:,.2f}")

        return "\n".join(sections)

    def _inventory_context(self) -> str:
        sections = [self.get_business_summary()]

        # All chemicals with details
        all_chemicals = execute_read_query(
            "SELECT chemical_name, chemical_code, quantity, min_quantity, unit, "
            "selling_price, purchase_price "
            "FROM chemicals "
            "ORDER BY chemical_name"
        )
        if all_chemicals:
            sections.append("\nAll Chemicals in Inventory:")
            for item in all_chemicals:
                low = " [LOW STOCK]" if float(item['quantity']) <= float(item['min_quantity']) else ""
                sections.append(
                    f"  - {item['chemical_name']} ({item['chemical_code']}): "
                    f"{item['quantity']} {item['unit']}{low} | "
                    f"Buy: INR {item['purchase_price']}, Sell: INR {item['selling_price']}"
                )

        # Category breakdown
        categories = execute_read_query(
            "SELECT cat.name, COUNT(ch.id) as count, SUM(ch.quantity) as total_qty "
            "FROM chemicals ch "
            "JOIN categories cat ON ch.category_id = cat.id "
            "GROUP BY cat.id, cat.name ORDER BY count DESC"
        )
        if categories:
            sections.append("\nInventory by Category:")
            for cat in categories:
                sections.append(f"  - {cat['name']}: {cat['count']} items, {cat['total_qty']} total units")

        return "\n".join(sections)

    def _customers_context(self) -> str:
        sections = [self.get_business_summary()]

        recent = execute_read_query(
            "SELECT first_name || ' ' || last_name as name, company_name, "
            "city, state, phone, email, is_active "
            "FROM customers "
            "ORDER BY created_at DESC LIMIT 10"
        )
        if recent:
            sections.append("\nRecent Customers:")
            for c in recent:
                status = "Active" if c.get('is_active') else "Inactive"
                company = f" ({c['company_name']})" if c.get('company_name') else ""
                location = f"{c.get('city', '')}, {c.get('state', '')}" if c.get('city') else ""
                sections.append(f"  - {c['name']}{company} - {location} [{status}]")

        return "\n".join(sections)

    def _orders_context(self) -> str:
        sections = [self.get_business_summary()]

        status_counts = execute_read_query(
            "SELECT status, COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total "
            "FROM orders GROUP BY status"
        )
        if status_counts:
            sections.append("\nOrders by Status:")
            for s in status_counts:
                sections.append(f"  - {s['status']}: {s['count']} orders, INR {s['total']:,.2f}")

        payment_counts = execute_read_query(
            "SELECT payment_status, COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total "
            "FROM orders GROUP BY payment_status"
        )
        if payment_counts:
            sections.append("\nOrders by Payment Status:")
            for p in payment_counts:
                sections.append(f"  - {p['payment_status']}: {p['count']} orders, INR {p['total']:,.2f}")

        return "\n".join(sections)


chat_context_service = ChatContextService()
