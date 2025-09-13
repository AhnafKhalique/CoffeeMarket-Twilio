"""Agent tools for CoffeeMarket voice assistant operations."""
from langchain_core.tools import tool
from loaders import COFFEE_DB, KNOWLEDGE_BASE, DELIVERY_STATUS_DB, INVENTORY_DB

@tool
def check_stock(product_name: str) -> str:
    """Check stock availability for coffee beans and equipment.
    
    Args:
        product_name: Name of the product to check (e.g., "Colombian Supremo", "French Press")
    
    Returns:
        String with stock information including availability, price, and restock dates if applicable
    """
    product_name_lower = product_name.lower().strip()
    
    # Search through coffee beans
    coffee_beans = INVENTORY_DB.get('coffee_beans', {})
    for product_id, product_info in coffee_beans.items():
        if product_name_lower in product_info['name'].lower():
            stock_level = product_info['stock_level']
            status = product_info['status']
            price = product_info['price']
            name = product_info['name']
            unit = product_info['unit']
            
            if status == "out_of_stock":
                expected_restock = product_info.get('expected_restock', 'Unknown')
                return f"{name} is currently out of stock. Expected restock date: {expected_restock}. Price: {price}"
            elif status == "low_stock":
                return f"{name} is running low! Only {stock_level} {unit} remaining. Price: {price}. We recommend ordering soon."
            else:
                return f"{name} is in stock! We have {stock_level} {unit} available. Price: {price}"
    
    # Search through equipment
    equipment = INVENTORY_DB.get('equipment', {})
    for product_id, product_info in equipment.items():
        if product_name_lower in product_info['name'].lower():
            stock_level = product_info['stock_level']
            status = product_info['status']
            price = product_info['price']
            name = product_info['name']
            unit = product_info['unit']
            
            if status == "out_of_stock":
                return f"{name} is currently out of stock. Price: {price}"
            elif status == "low_stock":
                return f"{name} is running low! Only {stock_level} {unit} remaining. Price: {price}. We recommend ordering soon."
            else:
                return f"{name} is in stock! We have {stock_level} {unit} available. Price: {price}"
    
    # Suggest similar products if no exact match found
    suggestions = []
    all_products = {}
    all_products.update(coffee_beans)
    all_products.update(equipment)
    
    for product_id, product_info in all_products.items():
        if any(word in product_info['name'].lower() for word in product_name_lower.split()):
            suggestions.append(product_info['name'])
    
    if suggestions:
        suggestion_text = ", ".join(suggestions[:3])  # Show up to 3 suggestions
        return f"I couldn't find '{product_name}' in our inventory. Did you mean: {suggestion_text}? Please try again with the exact product name."
    
    return f"I couldn't find '{product_name}' in our inventory. Please check the product name or ask about our available coffee beans and equipment."


@tool
def end_call(reason: str = "Customer request") -> str:
    """End the current call gracefully when customer is satisfied.
    
    ONLY use when customer says goodbye, thanks you, or indicates they're done.
    DO NOT use if customer wants to speak to a human - use escalate_to_human_agent instead.
    
    Args:
        reason: Reason for ending the call (e.g., "Customer satisfied", "Task completed")
    
    Returns:
        String with goodbye message that will be the final response before call ends
    """
    goodbye_messages = [
        "Thank you for calling CoffeeMarket! Have a wonderful day and enjoy your coffee!",
        "Thanks for choosing CoffeeMarket! We appreciate your business. Goodbye!",
        "It was great helping you today! Thank you for calling CoffeeMarket. Have a great day!",
        "Thank you for calling CoffeeMarket! We're here whenever you need us. Goodbye!",
        "Thanks for calling! Enjoy your coffee and have a fantastic day!"
    ]
    
    # Select goodbye message based on call ending reason
    if "help" in reason.lower() or "complete" in reason.lower():
        message = "Thank you for calling CoffeeMarket! I'm glad I could help you today. Have a wonderful day and enjoy your coffee!"
    elif "goodbye" in reason.lower() or "bye" in reason.lower():
        message = "Thank you for calling CoffeeMarket! Have a great day and enjoy your coffee!"
    else:
        # Default message
        message = goodbye_messages[0]
    
    # CALL_END marker triggers call termination
    return f"CALL_END:{message}"


@tool
def get_coffeemart_info(query: str) -> str:
    """Look up CoffeeMarket information including policies, hours, brewing guides, and company info.
    
    Args:
        query: The customer's question or topic they want information about
    
    Returns:
        Relevant information from the CoffeeMarket knowledge base
    """
    query_lower = query.lower()
    
    # Search knowledge base sections for relevant information
    relevant_info = []
    
    # Check company info
    if any(word in query_lower for word in ['hours', 'location', 'address', 'phone', 'contact']):
        company_info = KNOWLEDGE_BASE.get('company_info', {})
        if 'store_hours' in company_info:
            relevant_info.append(f"Store Hours: {company_info['store_hours']}")
        if 'locations' in company_info:
            locations = company_info['locations']
            for location in locations:
                relevant_info.append(f"{location['name']}: {location['address']}, Phone: {location['phone']}")
    
    # Check policies
    if any(word in query_lower for word in ['return', 'refund', 'policy', 'exchange', 'warranty']):
        policies = KNOWLEDGE_BASE.get('store_policies', {})
        if 'return_policy' in policies:
            policy = policies['return_policy']
            relevant_info.append(f"Return Policy: {policy['timeframe']} - {policy['conditions']}")
        if 'refund_policy' in policies:
            refund = policies['refund_policy']
            relevant_info.append(f"Refund Policy: {refund['processing_time']} - {refund['method']}")
    
    # Check loyalty program
    if any(word in query_lower for word in ['loyalty', 'rewards', 'points', 'member']):
        loyalty = KNOWLEDGE_BASE.get('loyalty_program', {})
        if loyalty:
            relevant_info.append(f"Loyalty Program: {loyalty.get('name', 'CoffeeMarket Rewards')}")
            if 'benefits' in loyalty:
                benefits = ', '.join(loyalty['benefits'])
                relevant_info.append(f"Benefits: {benefits}")
            if 'how_to_join' in loyalty:
                relevant_info.append(f"How to join: {loyalty['how_to_join']}")
    
    # Check sustainability
    if any(word in query_lower for word in ['sustainability', 'environment', 'eco', 'green', 'organic', 'fair trade']):
        sustainability = KNOWLEDGE_BASE.get('sustainability', {})
        if 'initiatives' in sustainability:
            initiatives = ', '.join(sustainability['initiatives'])
            relevant_info.append(f"Sustainability Initiatives: {initiatives}")
        if 'certifications' in sustainability:
            certs = ', '.join(sustainability['certifications'])
            relevant_info.append(f"Certifications: {certs}")
    
    # Check brewing guides
    if any(word in query_lower for word in ['brew', 'brewing', 'coffee', 'espresso', 'grind', 'ratio']):
        brewing = KNOWLEDGE_BASE.get('brewing_guides', {})
        for method, guide in brewing.items():
            if method in query_lower:
                relevant_info.append(f"{method.title()} Brewing: {guide.get('description', '')}")
                if 'steps' in guide:
                    steps = '. '.join(guide['steps'])
                    relevant_info.append(f"Steps: {steps}")
    
    # Check equipment care
    if any(word in query_lower for word in ['clean', 'maintenance', 'care', 'machine', 'grinder']):
        equipment = KNOWLEDGE_BASE.get('equipment_care', {})
        for item, care in equipment.items():
            if item in query_lower or any(keyword in query_lower for keyword in care.get('keywords', [])):
                relevant_info.append(f"{item.title()} Care: {care.get('description', '')}")
                if 'steps' in care:
                    steps = '. '.join(care['steps'])
                    relevant_info.append(f"Cleaning steps: {steps}")
    
    # Fallback to general company information
    if not relevant_info:
        company_info = KNOWLEDGE_BASE.get('company_info', {})
        if 'description' in company_info:
            relevant_info.append(company_info['description'])
        if 'specialties' in company_info:
            specialties = ', '.join(company_info['specialties'])
            relevant_info.append(f"We specialize in: {specialties}")
    
    if relevant_info:
        return '\n'.join(relevant_info)
    else:
        return "I'd be happy to help you with information about CoffeeMarket! Could you please be more specific about what you'd like to know? I can help with store hours, policies, brewing guides, our loyalty program, and more."


@tool
def get_delivery_status(order_number: str, include_details: bool = False) -> str:
    """Look up delivery status for a customer's order.
    
    Args:
        order_number: The order number to look up (e.g., CM12345)
        include_details: Whether to include tracking number, items, and total
    
    Returns:
        String with delivery status information
    """
    order_number = order_number.upper().strip()
    
    if order_number in DELIVERY_STATUS_DB:
        order = DELIVERY_STATUS_DB[order_number]
        status = order["status"]
        
        if status == "processing":
            basic_info = f"Order {order_number} is currently being processed. Expected to ship on {order['expected_ship']}."
            if include_details:
                basic_info += f" Items: {', '.join(order['items'])}. Total: {order['total']}"
            return basic_info
        elif status == "in_transit":
            basic_info = f"Order {order_number} shipped on {order['shipped_date']} and is in transit. Expected delivery: {order['expected_delivery']}."
            if include_details:
                basic_info += f" Tracking: {order['tracking_number']}. Items: {', '.join(order['items'])}. Total: {order['total']}"
            return basic_info
        elif status == "delivered":
            basic_info = f"Order {order_number} was delivered on {order['delivered_date']}."
            if include_details:
                basic_info += f" Tracking: {order['tracking_number']}. Items: {', '.join(order['items'])}. Total: {order['total']}"
            return basic_info
        elif status == "confirmed":
            basic_info = f"Order {order_number} has been confirmed and will ship on {order['expected_ship']}."
            if include_details:
                basic_info += f" Items: {', '.join(order['items'])}. Total: {order['total']}"
            return basic_info
    else:
        return f"I couldn't find order {order_number} in our system. Please double-check the order number or contact customer service if you need further assistance."


@tool
def escalate_to_human_agent(reason: str = "Customer requested human assistance") -> str:
    """Transfer customer to human agent when they request human assistance.
    
    Use when customers say "I want to speak to a human", "Can I talk to someone?",
    or when they have complex issues requiring human judgment.
    
    Args:
        reason: Brief description of why escalation is needed
        
    Returns:
        A message indicating the transfer is being initiated
    """
    # HANDOFF_HUMAN marker triggers agent transfer
    message = f"I understand you'd like to speak with one of our team members. Let me connect you with a human agent right away. Please hold on for just a moment while I transfer your call."
    
    # Marker processed by conversation handler for transfer
    return f"HANDOFF_HUMAN:{message}"


@tool
def get_coffee_recommendations(preferences: str) -> str:
    """Get coffee recommendations based on customer preferences.
    
    Args:
        preferences: Customer preferences like "strong", "mild", "chocolate notes", "fruity", "espresso"
    
    Returns:
        String with coffee recommendations and details
    """
    if not COFFEE_DB or 'coffee_beans' not in COFFEE_DB:
        return "I'm sorry, I don't have access to our coffee database right now. Please contact customer service for recommendations."
    
    preferences_lower = preferences.lower()
    recommendations = []
    
    # Analyze coffee database for preference matches
    for category_name, category in COFFEE_DB['coffee_beans'].items():
        for coffee_key, coffee in category.items():
            coffee_name = coffee.get('name', coffee_key)
            description = coffee.get('description', '')
            taste_profile = coffee.get('taste_profile', {})
            flavor_notes = taste_profile.get('flavor_notes', [])
            strength = coffee.get('strength', '')
            price = coffee.get('price', '')
            brewing_methods = coffee.get('brewing_methods', [])
            
            # Score coffee against customer preferences
            match_score = 0
            match_reasons = []
            
            # Match strength requirements
            if any(word in preferences_lower for word in ['strong', 'bold', 'intense']):
                if 'strong' in strength.lower() or 'full' in taste_profile.get('body', '').lower():
                    match_score += 3
                    match_reasons.append("strong flavor")
            
            if any(word in preferences_lower for word in ['mild', 'light', 'smooth']):
                if 'light' in strength.lower() or 'medium' in strength.lower():
                    match_score += 3
                    match_reasons.append("smooth taste")
            
            # Match flavor profile preferences
            flavor_keywords = {
                'chocolate': ['chocolate', 'cocoa'],
                'fruity': ['berry', 'fruit', 'citrus', 'orange', 'lemon', 'blueberry'],
                'nutty': ['nuts', 'nutty', 'almond'],
                'floral': ['floral', 'tea-like', 'bergamot'],
                'spicy': ['spice', 'spicy', 'cedar'],
                'sweet': ['caramel', 'vanilla', 'honey', 'sugar']
            }
            
            for pref_key, keywords in flavor_keywords.items():
                if pref_key in preferences_lower:
                    if any(keyword.lower() in [note.lower() for note in flavor_notes] for keyword in keywords):
                        match_score += 2
                        match_reasons.append(f"{pref_key} notes")
            
            # Match brewing method requirements
            if 'espresso' in preferences_lower and 'Espresso' in brewing_methods:
                match_score += 2
                match_reasons.append("great for espresso")
            
            if 'french press' in preferences_lower and 'French press' in brewing_methods:
                match_score += 2
                match_reasons.append("perfect for French press")
            
            # Include coffee if match score is sufficient
            if match_score >= 2:
                recommendations.append({
                    'name': coffee_name,
                    'score': match_score,
                    'reasons': match_reasons,
                    'description': description,
                    'flavor_notes': flavor_notes,
                    'price': price,
                    'strength': strength
                })
    
    # Return top 3 recommendations by match score
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    top_recommendations = recommendations[:3]
    
    if not top_recommendations:
        # Default recommendations if no matches found
        return "Based on your preferences, I'd recommend our Colombian Supremo for a balanced, smooth cup, or our House Blend for everyday drinking. Both are versatile and well-loved by our customers!"
    
    # Format recommendations for customer
    response = "Here are my top recommendations for you:\n\n"
    for i, rec in enumerate(top_recommendations, 1):
        reasons_text = ", ".join(rec['reasons'])
        flavor_text = ", ".join(rec['flavor_notes'][:3])  # Show top 3 flavor notes
        
        response += f"{i}. **{rec['name']}** ({rec['price']})\n"
        response += f"   Perfect because: {reasons_text}\n"
        response += f"   Flavor notes: {flavor_text}\n"
        response += f"   Strength: {rec['strength']}\n\n"
    
    response += "Would you like more details about any of these, or do you have other preferences to consider?"
    
    return response
