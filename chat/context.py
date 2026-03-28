import logging
from database import execute_read_query

logger = logging.getLogger(__name__)


class ChatContextService:
    """Reads ERP database to build LLM context for chat."""

    def get_business_summary(self) -> str:
        """Get a high-level business summary for LLM context."""
        sections = []

        # Customer stats
        customers = execute_read_query(
            "SELECT COUNT(*) as total, SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active "
            "FROM customers_customer"
        )
        if customers:
            c = customers[0]
            sections.append(f"Customers: {c['total']} total, {c['active']} active")

        # Order stats
        orders = execute_read_query(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending, "
            "SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered "
            "FROM orders_order"
        )
        if orders:
            o = orders[0]
            sections.append(f"Orders: {o['total']} total, {o['pending']} pending, {o['delivered']} delivered")

        # Revenue
        revenue = execute_read_query(
            "SELECT COALESCE(SUM(total_amount), 0) as total_revenue "
            "FROM orders_order WHERE payment_status = 'paid'"
        )
        if revenue:
            sections.append(f"Total Revenue (paid): INR {revenue[0]['total_revenue']:,.2f}")

        # Inventory
        inventory = execute_read_query(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN quantity <= min_quantity THEN 1 ELSE 0 END) as low_stock "
            "FROM inventory_chemical"
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

    def _general_context(self) -> str:
        return self.get_business_summary()

    def _sales_context(self) -> str:
        sections = [self.get_business_summary()]

        # Recent orders
        recent = execute_read_query(
            "SELECT o.order_number, o.total_amount, o.status, o.payment_status, "
            "c.first_name || ' ' || c.last_name as customer_name "
            "FROM orders_order o "
            "JOIN customers_customer c ON o.customer_id = c.id "
            "ORDER BY o.created_at DESC LIMIT 10"
        )
        if recent:
            sections.append("\nRecent Orders:")
            for r in recent:
                sections.append(
                    f"  - {r['order_number']}: INR {r['total_amount']:,.2f} "
                    f"({r['status']}, {r['payment_status']}) - {r['customer_name']}"
                )

        # Top customers by revenue
        top = execute_read_query(
            "SELECT c.first_name || ' ' || c.last_name as name, "
            "c.company_name, SUM(o.total_amount) as total "
            "FROM orders_order o "
            "JOIN customers_customer c ON o.customer_id = c.id "
            "WHERE o.payment_status = 'paid' "
            "GROUP BY o.customer_id ORDER BY total DESC LIMIT 5"
        )
        if top:
            sections.append("\nTop Customers by Revenue:")
            for t in top:
                company = f" ({t['company_name']})" if t.get('company_name') else ""
                sections.append(f"  - {t['name']}{company}: INR {t['total']:,.2f}")

        return "\n".join(sections)

    def _inventory_context(self) -> str:
        sections = [self.get_business_summary()]

        # Low stock items
        low_stock = execute_read_query(
            "SELECT chemical_name, quantity, min_quantity, unit, selling_price "
            "FROM inventory_chemical "
            "WHERE quantity <= min_quantity "
            "ORDER BY quantity ASC LIMIT 10"
        )
        if low_stock:
            sections.append("\nLow Stock Items (need reorder):")
            for item in low_stock:
                sections.append(
                    f"  - {item['chemical_name']}: {item['quantity']} {item['unit']} "
                    f"(min: {item['min_quantity']})"
                )

        # Category breakdown
        categories = execute_read_query(
            "SELECT cat.name, COUNT(ch.id) as count, SUM(ch.quantity) as total_qty "
            "FROM inventory_chemical ch "
            "JOIN inventory_category cat ON ch.category_id = cat.id "
            "GROUP BY cat.id ORDER BY count DESC"
        )
        if categories:
            sections.append("\nInventory by Category:")
            for cat in categories:
                sections.append(f"  - {cat['name']}: {cat['count']} items, {cat['total_qty']} total units")

        return "\n".join(sections)

    def _customers_context(self) -> str:
        sections = [self.get_business_summary()]

        # Recent customers
        recent = execute_read_query(
            "SELECT first_name || ' ' || last_name as name, company_name, "
            "city, state, phone, email, is_active "
            "FROM customers_customer "
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

        # Order status breakdown
        status_counts = execute_read_query(
            "SELECT status, COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total "
            "FROM orders_order GROUP BY status"
        )
        if status_counts:
            sections.append("\nOrders by Status:")
            for s in status_counts:
                sections.append(f"  - {s['status']}: {s['count']} orders, INR {s['total']:,.2f}")

        # Payment status breakdown
        payment_counts = execute_read_query(
            "SELECT payment_status, COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total "
            "FROM orders_order GROUP BY payment_status"
        )
        if payment_counts:
            sections.append("\nOrders by Payment Status:")
            for p in payment_counts:
                sections.append(f"  - {p['payment_status']}: {p['count']} orders, INR {p['total']:,.2f}")

        return "\n".join(sections)


chat_context_service = ChatContextService()
