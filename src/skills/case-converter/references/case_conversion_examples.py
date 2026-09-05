"""
Example usage patterns for case-converter skill.
Demonstrates various case conversion workflows (camelCase, snake_case, PascalCase, kebab-case).
"""

# Example 1: Converting a variable name to camelCase
# python scripts/case_converter.py "user_profile_data" --to camel
# Result: userProfileData

# Example 2: Converting to CONSTANT_CASE
# python scripts/case_converter.py "max_retry_count" --to constant
# Result: MAX_RETRY_COUNT

# Example 3: Converting a file of identifiers
# python scripts/case_converter.py --file input_identifiers.txt --to kebab --output result.txt
