import re
from datetime import datetime
from typing import List

def extract_quarters_fy(text: str) -> List[str]:
    """
    Extract quarters and financial years from input string.
    Returns standardized format: ['Q1FY23', 'Q4FY25', etc.]
    """
    text = text.strip()
    results = []
    
    # Current date for "last X quarters" calculations
    current_date = datetime.now()
    current_month = current_date.month
    
    # Determine current quarter and FY (assuming FY starts in April)
    if current_month >= 4:  # Apr-Mar FY
        current_fy = current_date.year + 1
        if current_month >= 4 and current_month <= 6:
            current_quarter = 1
        elif current_month >= 7 and current_month <= 9:
            current_quarter = 2
        elif current_month >= 10 and current_month <= 12:
            current_quarter = 3
    else:
        current_fy = current_date.year
        current_quarter = 4
    
    # Handle "last X quarters"
    last_quarters_match = re.search(r'last\s+(\d+)\s+quarters?', text, re.IGNORECASE)
    if last_quarters_match:
        num_quarters = int(last_quarters_match.group(1))
        q, fy = current_quarter, current_fy
        
        for _ in range(num_quarters):
            results.append(f"Q{q}FY{str(fy)[2:]}")
            q -= 1
            if q == 0:
                q = 4
                fy -= 1
        return results
    
    # Handle "different quarters in/of/for FY/Financial Year/Fiscal Year YYYY"
    different_quarters_match = re.search(r'different\s+quarters\s+(?:in|of|for)\s+(?:fy|financial\s+year|fiscal\s+year)\s*(\d{2,4})', text, re.IGNORECASE)
    if different_quarters_match:
        year = different_quarters_match.group(1)
        fy_suffix = year[2:] if len(year) == 4 else year
        return [f"Q{i}FY{fy_suffix}" for i in range(1, 5)]
    
    # Comprehensive regex patterns for various formats
    patterns = [
        # Quarter X, FY/Financial Year/Fiscal Year YYYY
        r'quarter\s+(\d+),?\s+(?:fy|financial\s+year|fiscal\s+year)\s*(\d{2,4})',
        # QX FY/Financial Year/Fiscal Year YYYY  
        r'q(\d+)\s+(?:fy|financial\s+year|fiscal\s+year)\s*(\d{2,4})',
        # QX FYXX (compact format)
        r'q(\d+)fy(\d{2,4})',
        # XX YYYY (quarter number and year)
        r'(\d+)\s+(\d{4})',
        # Quarter X Financial/Fiscal Year YYYY
        r'quarter\s+(\d+)\s+(?:financial|fiscal)\s+year\s+(\d{4})',
        # In Financial/Fiscal Year YYYY, Quarter X
        r'(?:in\s+)?(?:financial|fiscal)\s+year\s+(\d{4}),?\s+quarter\s+(\d+)',
        # Show me Quarter X Financial Year YYYY
        r'show\s+me\s+quarter\s+(\d+)\s+financial\s+year\s+(\d{4})',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            groups = match.groups()
            
            # Handle different group orders
            if 'financial year' in pattern.lower() or 'fiscal year' in pattern.lower():
                if 'in.*quarter' in pattern:
                    # Year comes first, then quarter
                    year, quarter = groups[0], groups[1]
                else:
                    # Quarter comes first, then year
                    quarter, year = groups[0], groups[1]
            else:
                quarter, year = groups[0], groups[1]
            
            # Format quarter (pad single digits with 0 for certain formats)
            quarter = quarter.zfill(2) if pattern == r'(\d+)\s+(\d{4})' else quarter
            
            # Format year to 2 digits
            fy_suffix = year[2:] if len(year) == 4 else year.zfill(2)
            
            # Create standardized format
            q_prefix = f"{quarter.zfill(2)}" if pattern == r'(\d+)\s+(\d{4})' else f"Q{quarter}"
            results.append(f"{q_prefix}FY{fy_suffix}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_results = []
    for item in results:
        if item not in seen:
            seen.add(item)
            unique_results.append(item)
    
    return unique_results


# Test cases
test_cases = [
    "Quarter 4, FY25",
    "Q4 FY25", 
    "Q3FY23",
    "Q2 2020",
    "Q3 FY23",
    "Q4 Financial Year 2023",
    "Q2 Fiscal Year 2022",
    "Q4 Fy20, Q2 Financial Year 2021",
    "last 4 quarters",
    "last 2 quarters", 
    "different quarters in FY23",
    "different quarters of Financial Year 2021",
    "different quarters for Fiscal Year 2020",
    "Q1 FY24 and 03 FY24",
    "Performance, in Quarter 2 FY22 vs Q4 FY22",
    "Compare Q1 FY2021 and Q2 2021",
    "Q3 FY2020 results and 01 FY2021 commentary",
    "q2 2019, Q4 2020, and q1 FY21",
    "In Fiscal Year 2022, Quarter 3 was better",
    "Show me Quarter 1 Financial Year 2020",
    "My name is Bhavesh"
]

# Run tests
print("Testing quarter and FY extraction:")
print("-" * 50)
for test in test_cases:
    result = extract_quarters_fy(test)
    print(f'"{test}" -> {result}')