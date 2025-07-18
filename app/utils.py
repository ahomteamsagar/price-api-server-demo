import requests
def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """
    Get the exchange rate from one currency to another using open.er-api.com.
    
    Args:
        from_currency (str): The base currency (e.g., "USD").
        to_currency (str): The target currency (e.g., "EUR").

    Returns:
        float: The exchange rate, e.g., 1 USD = X EUR

    Raises:
        ValueError: If the API call fails or the currency is not supported.
    """
    url = f"https://open.er-api.com/v6/latest/{from_currency.upper()}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data["result"] != "success":
            raise ValueError(f"API error: {data.get('error-type', 'Unknown error')}")
        
        rates = data.get("rates", {})
        if to_currency.upper() not in rates:
            raise ValueError(f"Currency {to_currency} not found in rates.")
        
        return rates[to_currency.upper()]
    
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Request failed: {e}")
