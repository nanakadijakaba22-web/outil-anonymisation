"""
Test script to verify generalization corrections.
Tests postal codes, dates, and numeric ranges.
"""
import pandas as pd
from datetime import datetime

# Simulate the generalization methods

def generalize_postal_code(value, prefix_length=3):
    """
    Generalize postal code by keeping prefix and replacing rest with asterisks.
    
    Examples:
        "G1X 3J4" -> "G1X ***" (prefix_length=3)
        "H3B1A1" -> "H3B ***" (prefix_length=3)
        "K1A 0B1" -> "K1A ***" (prefix_length=3)
    """
    if pd.isna(value):
        return value
    
    postal_str = str(value).strip()
    
    # Remove spaces and dashes for processing
    postal_clean = postal_str.replace(" ", "").replace("-", "")
    
    # Keep prefix and replace rest with asterisks
    if len(postal_clean) > prefix_length:
        prefix = postal_clean[:prefix_length]
        # Use *** for visual consistency
        return f"{prefix} ***"
    else:
        # If too short, just return as is
        return postal_str

def generalize_to_range(value, range_size=10):
    """Convert numeric value to range string."""
    try:
        num = float(value)
        lower = int(num // range_size) * range_size
        upper = lower + range_size
        return f"{lower}-{upper}"
    except (ValueError, TypeError):
        return str(value)


# Test postal codes
print("=" * 60)
print("TEST 1: Généralisation des codes postaux")
print("=" * 60)
postal_codes = ["G1X 3J4", "H3B1A1", "K1A 0B1", "M5V-2T6", "V6B 4Y8"]
for code in postal_codes:
    result = generalize_postal_code(code, 3)
    print(f"{code:15} -> {result}")

# Test dates
print("\n" + "=" * 60)
print("TEST 2: Généralisation des dates")
print("=" * 60)
dates = ["2024-05-15", "2023-12-01", "2022-01-30"]
df_dates = pd.DataFrame({"date": pd.to_datetime(dates)})

# Year only
df_dates["year_only"] = df_dates["date"].dt.year

# Year-Month
df_dates["year_month"] = df_dates["date"].dt.strftime('%Y-%m')

print("\nOriginal        | Year Only | Year-Month")
print("-" * 60)
for idx, row in df_dates.iterrows():
    print(f"{row['date'].strftime('%Y-%m-%d')}    | {row['year_only']}      | {row['year_month']}")

# Test numeric ranges
print("\n" + "=" * 60)
print("TEST 3: Généralisation des valeurs numériques (tranches)")
print("=" * 60)
ages = [25, 34, 42, 56, 61, 78]
print("\nTranche de 10:")
for age in ages:
    result = generalize_to_range(age, 10)
    print(f"Age {age:2} -> {result}")

print("\nTranche de 20:")
for age in ages:
    result = generalize_to_range(age, 20)
    print(f"Age {age:2} -> {result}")

print("\n" + "=" * 60)
print("✓ Tous les tests ont été exécutés avec succès!")
print("=" * 60)
